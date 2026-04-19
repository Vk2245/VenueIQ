"""
VenueIQ Incident Reporting Router.

Handles incident creation, listing, and status updates. Attendees
can report issues with photo and GPS evidence; AI categorizes severity
and routes to the correct staff team. Supports the Real-Time Coordination
challenge of the Physical Event Experience problem statement.
"""

from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, status

from config import settings
from models import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdateRequest,
)
from services import firestore_service, gemini_service
from services.notification_service import log_event, notify_incident_team

router = APIRouter(prefix="/api/venue", tags=["Incident Management"])


@router.post(
    "/{venue_id}/incident",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a venue incident",
    description="Attendees can report issues (spills, overcrowding, safety hazards) "
    "with photo + GPS evidence. Gemini AI categorizes severity and routes "
    "to the correct staff team for rapid response.",
)
async def create_incident(
    venue_id: str,
    incident: IncidentCreate,
) -> IncidentResponse:
    """Create a new incident report with AI severity assessment.

    Accepts attendee reports of venue issues, uses Gemini AI to
    assess severity, and automatically routes the incident to the
    appropriate response team. Supports real-time coordination.

    Args:
        venue_id: The venue identifier.
        incident: Incident details including category, description, and location.

    Returns:
        IncidentResponse with AI-assessed severity and team assignment.
    """
    # Verify reCAPTCHA token if configured
    if settings.recaptcha_secret_key and not settings.demo_mode:
        if not incident.recaptcha_token:
            raise HTTPException(status_code=400, detail="reCAPTCHA token required")
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.recaptcha_secret_key,
                    "response": incident.recaptcha_token,
                },
            )
            data = resp.json()
            if not data.get("success") or data.get("score", 0) < 0.5:
                raise HTTPException(status_code=403, detail="Bot activity detected")

    # AI severity assessment
    ai_assessment = await gemini_service.assess_incident_severity(
        category=incident.category.value,
        description=incident.description,
        zone_name=incident.zone_name,
    )

    # Build incident data
    incident_data = incident.model_dump()
    incident_data["venue_id"] = venue_id
    incident_data["category"] = incident.category.value
    incident_data["severity"] = ai_assessment.get("severity", "medium")
    incident_data["assigned_team"] = ai_assessment.get("assigned_team", "General Staff")
    incident_data["ai_assessment"] = ai_assessment.get("ai_assessment", "")
    incident_data["status"] = "reported"

    # Remove photo from storage (keep reference only)
    if "photo_base64" in incident_data:
        incident_data["has_photo"] = incident_data.get("photo_base64") is not None
        incident_data.pop("photo_base64", None)

    # Save to database
    incident_id = await firestore_service.save_incident(incident_data)

    # Notify assigned team
    await notify_incident_team(
        venue_id=venue_id,
        incident_id=incident_id,
        severity=ai_assessment.get("severity", "medium"),
        assigned_team=ai_assessment.get("assigned_team", "General Staff"),
        zone_name=incident.zone_name,
        description=incident.description,
    )

    log_event(
        "incident_created",
        f"Incident created in {incident.zone_name}: {incident.category.value}",
        severity="WARNING",
        metadata={
            "incident_id": incident_id,
            "severity": ai_assessment.get("severity"),
            "venue_id": venue_id,
        },
    )

    return IncidentResponse(
        incident_id=incident_id,
        venue_id=venue_id,
        category=incident.category.value,
        severity=ai_assessment.get("severity", "medium"),
        description=incident.description,
        zone_name=incident.zone_name,
        status="reported",
        assigned_team=ai_assessment.get("assigned_team", "General Staff"),
        ai_assessment=ai_assessment.get("ai_assessment", ""),
        latitude=incident.latitude,
        longitude=incident.longitude,
    )


@router.get(
    "/{venue_id}/incidents",
    response_model=List[IncidentResponse],
    summary="List venue incidents",
    description="Retrieve all incidents for a venue, sorted by creation time. "
    "Supports filtering by severity for prioritized response.",
)
async def list_incidents(
    venue_id: str,
    severity: str = None,
) -> List[IncidentResponse]:
    """List all incidents for a venue with optional severity filter.

    Returns all incident reports for a venue, enabling staff to
    prioritize response based on severity and category.

    Args:
        venue_id: The venue identifier.
        severity: Optional severity filter (low, medium, high, critical).

    Returns:
        List of IncidentResponse with incident details.
    """
    incidents = await firestore_service.get_incidents(venue_id)

    if severity:
        incidents = [
            inc for inc in incidents
            if inc.get("severity") == severity
        ]

    return [
        IncidentResponse(
            incident_id=inc.get("incident_id", ""),
            venue_id=inc.get("venue_id", venue_id),
            category=inc.get("category", "other"),
            severity=inc.get("severity", "medium"),
            description=inc.get("description", ""),
            zone_name=inc.get("zone_name", ""),
            status=inc.get("status", "reported"),
            assigned_team=inc.get("assigned_team", ""),
            ai_assessment=inc.get("ai_assessment", ""),
            latitude=inc.get("latitude"),
            longitude=inc.get("longitude"),
            created_at=inc.get("created_at", 0),
        )
        for inc in incidents
    ]


@router.put(
    "/{venue_id}/incident/{incident_id}",
    summary="Update incident status",
    description="Update the status of an incident (acknowledged, in_progress, resolved). "
    "Used by staff teams to track incident resolution.",
)
async def update_incident(
    venue_id: str,
    incident_id: str,
    update: IncidentUpdateRequest,
) -> Dict[str, Any]:
    """Update an incident's status and resolution notes.

    Enables staff teams to track incident lifecycle from
    reported → acknowledged → in_progress → resolved.

    Args:
        venue_id: The venue identifier.
        incident_id: The incident identifier to update.
        update: Status update data.

    Returns:
        Confirmation of the status update.

    Raises:
        HTTPException: 404 if incident not found.
    """
    update_data = {
        "status": update.status.value,
    }
    if update.resolution_notes:
        update_data["resolution_notes"] = update.resolution_notes

    success = await firestore_service.update_incident(incident_id, update_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    log_event(
        "incident_updated",
        f"Incident {incident_id} status updated to {update.status.value}",
        metadata={"incident_id": incident_id, "venue_id": venue_id},
    )

    return {
        "message": "Incident updated successfully",
        "incident_id": incident_id,
        "new_status": update.status.value,
    }
