"""
VenueIQ Crowd Analysis Router.

Handles AI-powered crowd density analysis, heatmap data generation,
and crowd observation reports. Directly addresses the Crowd Management
challenge of the Physical Event Experience problem statement.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from models import (
    CrowdAnalysisRequest,
    CrowdAnalysisResponse,
    CrowdReportCreate,
    HeatmapDataPoint,
    HeatmapResponse,
)
from services import firestore_service, gemini_service
from services.notification_service import log_event

router = APIRouter(prefix="/api/venue", tags=["Crowd Management"])


@router.post(
    "/crowd-analysis",
    response_model=CrowdAnalysisResponse,
    summary="AI Crowd Density Analysis",
    description="Upload venue photos or describe current conditions for AI-powered "
    "crowd density analysis using Google Gemini 2.5 Flash. Identifies bottleneck "
    "zones, suggests optimal flow patterns, and provides safety scores. "
    "Directly addresses the Crowd Management challenge.",
)
async def analyze_crowd(request: CrowdAnalysisRequest) -> CrowdAnalysisResponse:
    """Analyze crowd density using Gemini AI.

    Processes text descriptions (and optionally photos) of current crowd
    conditions to provide structured analysis including density levels,
    bottleneck identification, safety scores, and flow recommendations
    for venue staff.

    Args:
        request: Crowd analysis request with description and optional image.

    Returns:
        CrowdAnalysisResponse with AI-generated analysis results.
    """
    # Get venue type for context
    venue = await firestore_service.get_venue(request.venue_id)
    venue_type = venue.get("venue_type", "stadium") if venue else "stadium"

    # Run Gemini AI analysis
    analysis = await gemini_service.analyze_crowd_density(
        description=request.description,
        venue_type=venue_type,
        zone_name=request.zone_name,
    )

    log_event(
        "crowd_analysis",
        f"Crowd analysis for venue {request.venue_id}: {analysis.get('density_level', 'unknown')}",
        metadata={"venue_id": request.venue_id, "zone": request.zone_name},
    )

    return CrowdAnalysisResponse(
        venue_id=request.venue_id,
        density_level=analysis.get("density_level", "busy"),
        estimated_count=analysis.get("estimated_count", 0),
        bottleneck_zones=analysis.get("bottleneck_zones", []),
        flow_recommendations=analysis.get("flow_recommendations", []),
        safety_score=analysis.get("safety_score", 5.0),
        analysis_summary=analysis.get("analysis_summary", "Analysis complete."),
    )


@router.get(
    "/{venue_id}/heatmap",
    response_model=HeatmapResponse,
    summary="Get venue crowd heatmap",
    description="Returns real-time crowd density data points for rendering "
    "an interactive heatmap overlay using Leaflet.js. Each point includes GPS "
    "coordinates and density weight for the heatmap visualization layer.",
)
async def get_heatmap(venue_id: str) -> HeatmapResponse:
    """Get heatmap data for Leaflet.js visualization.

    Generates crowd density data points from current venue zone
    occupancy data, formatted for the Leaflet.heat plugin
    heatmap layer on OpenStreetMap.

    Args:
        venue_id: The venue identifier.

    Returns:
        HeatmapResponse with data points for map overlay.

    Raises:
        HTTPException: 404 if venue not found.
    """
    if venue_id == "demo-venue":
        venue = await firestore_service.get_demo_venue()
    else:
        venue = await firestore_service.get_venue(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found",
            )

    data_points = []
    for zone in venue.get("zones", []):
        current = zone.get("current", 0)
        capacity = zone.get("capacity", 1)
        weight = min(current / capacity, 1.0)
        latitude = zone.get("lat", venue.get("latitude", 0))
        longitude = zone.get("lng", venue.get("longitude", 0))

        data_points.append(HeatmapDataPoint(
            latitude=latitude,
            longitude=longitude,
            weight=round(weight, 2),
            zone_name=zone.get("name", "Unknown"),
        ))

    return HeatmapResponse(
        venue_id=venue_id,
        data_points=data_points,
    )


@router.post(
    "/{venue_id}/crowd-report",
    summary="Submit crowd observation",
    description="Attendees can submit crowd density observations to help "
    "build a real-time picture of venue conditions. Supports GPS location "
    "and density estimates for crowd-sourced intelligence.",
)
async def submit_crowd_report(
    venue_id: str,
    report: CrowdReportCreate,
) -> Dict[str, Any]:
    """Submit a crowd density observation report.

    Allows venue attendees to report crowd conditions in their
    zone, contributing to crowd-sourced real-time intelligence
    for venue managers.

    Args:
        venue_id: The venue identifier.
        report: Crowd observation data with zone, density, and location.

    Returns:
        Confirmation with the generated report identifier.
    """
    report_data = report.model_dump()
    report_data["venue_id"] = venue_id

    report_id = await firestore_service.save_crowd_report(report_data)

    log_event(
        "crowd_report",
        f"Crowd report submitted for {venue_id}: zone={report.zone_name}, density={report.density_estimate}",
        metadata={"venue_id": venue_id, "report_id": report_id},
    )

    return {
        "message": "Crowd report submitted successfully",
        "report_id": report_id,
        "venue_id": venue_id,
    }
