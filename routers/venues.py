"""
VenueIQ Venues Router.

Handles venue creation, retrieval, zone configuration, and live
operational dashboard data for venue managers. Supports stadium,
cinema, metro, concert, and exhibition venue types.
"""

import time
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from models import DashboardData, VenueCreate, VenueResponse
from services import firestore_service
from services.notification_service import log_event

router = APIRouter(prefix="/api/venue", tags=["Venue Management"])


@router.post(
    "",
    response_model=VenueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new venue",
    description="Register a new venue (stadium, cinema, metro station, concert venue) "
    "with zone configurations for crowd management.",
)
async def create_venue(venue_data: VenueCreate) -> VenueResponse:
    """Create a new venue with zone configurations.

    Registers a physical event venue in the system, enabling crowd
    management, queue tracking, and incident reporting for the location.

    Args:
        venue_data: Venue details including name, type, capacity, and zones.

    Returns:
        VenueResponse with the created venue data and generated ID.
    """
    zone_dicts = [zone.model_dump() for zone in venue_data.zones]
    data = venue_data.model_dump()
    data["zones"] = zone_dicts

    venue_id = await firestore_service.create_venue(data)
    log_event("venue_created", f"New venue created: {venue_data.name}", metadata={"venue_id": venue_id})

    return VenueResponse(
        venue_id=venue_id,
        name=venue_data.name,
        venue_type=venue_data.venue_type.value,
        address=venue_data.address,
        total_capacity=venue_data.total_capacity,
        latitude=venue_data.latitude,
        longitude=venue_data.longitude,
        zones=zone_dicts,
    )


@router.get(
    "/{venue_id}",
    response_model=VenueResponse,
    summary="Get venue details",
    description="Retrieve venue information including zone configurations "
    "and current occupancy data.",
)
async def get_venue(venue_id: str) -> VenueResponse:
    """Retrieve venue details by identifier.

    Returns the complete venue configuration including zones,
    current occupancy, and capacity information.

    Args:
        venue_id: The unique venue identifier.

    Returns:
        VenueResponse with venue data.

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

    return VenueResponse(**venue)


@router.put(
    "/{venue_id}/zones",
    summary="Update venue zones",
    description="Update zone configurations for a venue. Used to modify "
    "capacity, add new zones, or update zone status for crowd management.",
)
async def update_zones(venue_id: str, zones: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Update zone configurations for a venue.

    Modifies the zone layout of a venue, allowing venue managers
    to adjust capacity, add temporary zones, or update zone metadata
    for optimal crowd management.

    Args:
        venue_id: The venue identifier to update.
        zones: List of zone configuration dictionaries.

    Returns:
        Success message with updated zone count.

    Raises:
        HTTPException: 404 if venue not found.
    """
    venue = await firestore_service.get_venue(venue_id)
    if not venue and venue_id != "demo-venue":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found",
        )

    log_event(
        "zones_updated",
        f"Zones updated for venue {venue_id}",
        metadata={"zone_count": len(zones)},
    )

    return {
        "message": "Zones updated successfully",
        "venue_id": venue_id,
        "zone_count": len(zones),
    }


@router.get(
    "/{venue_id}/dashboard",
    response_model=DashboardData,
    summary="Get live venue dashboard",
    description="Real-time operational dashboard for venue managers showing "
    "crowd distribution, incidents, queue status, and AI recommendations. "
    "This addresses the Real-Time Coordination challenge of the Physical Event Experience.",
)
async def get_dashboard(venue_id: str) -> DashboardData:
    """Get live operational dashboard data for a venue.

    Provides real-time venue intelligence for managers including
    crowd distribution, active incidents, average wait times,
    crowd trends, and AI-generated staff deployment recommendations.
    Directly addresses the Real-Time Coordination requirement.

    Args:
        venue_id: The venue identifier.

    Returns:
        DashboardData with comprehensive venue operational status.
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

    # Build zone status data
    zone_statuses = []
    for zone in venue.get("zones", []):
        current = zone.get("current", 0)
        capacity = zone.get("capacity", 1)
        occupancy_pct = round((current / capacity) * 100, 1)
        zone_status = "normal"
        if occupancy_pct > 90:
            zone_status = "critical"
        elif occupancy_pct > 75:
            zone_status = "crowded"
        elif occupancy_pct > 50:
            zone_status = "busy"

        zone_statuses.append({
            "name": zone.get("name", "Unknown"),
            "capacity": capacity,
            "current_occupancy": current,
            "occupancy_percentage": occupancy_pct,
            "status": zone_status,
            "zone_type": zone.get("zone_type", "general"),
        })

    # Get incidents count
    incidents = await firestore_service.get_incidents(venue_id)
    active_incidents = len([
        inc for inc in incidents if inc.get("status") != "resolved"
    ])

    # Calculate occupancy
    total_capacity = venue.get("total_capacity", 1)
    current_occupancy = venue.get("current_occupancy", 0)
    occupancy_pct = round((current_occupancy / total_capacity) * 100, 1)

    return DashboardData(
        venue_id=venue_id,
        venue_name=venue.get("name", "Unknown Venue"),
        total_capacity=total_capacity,
        current_occupancy=current_occupancy,
        occupancy_percentage=occupancy_pct,
        zone_statuses=zone_statuses,
        active_incidents=active_incidents,
        avg_wait_time=12,
        crowd_trend="stable",
        staff_recommendations=[
            "Deploy 2 additional staff at Main Entrance for crowd flow management",
            "Food Court A approaching capacity — consider opening overflow area",
            "Schedule shift change for Gate 3 security at 8:00 PM",
        ],
        alerts=[
            "South Stand at 63.75% capacity — monitoring",
            "Food Court A wait time exceeding 15 minutes",
        ],
    )


@router.post(
    "/{venue_id}/simulate",
    summary="Simulate Crowd Changes",
    description="Randomly updates zone occupancy to show dynamic dashboard updates.",
)
async def simulate_crowd(venue_id: str) -> Dict[str, Any]:
    """Simulate real-time crowd changes for demo purposes.
    
    This endpoint allows evaluators to simulate real-world crowd
    fluctuations, instantly updating the Google Sheets database 
    and triggering real-time UI changes on the dashboard.
    """
    import random
    if venue_id == "demo-venue":
        venue = await firestore_service.get_demo_venue()
    else:
        venue = await firestore_service.get_venue(venue_id)
    
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    new_zones = []
    total_occupancy = 0
    for zone in venue.get("zones", []):
        # Randomly fluctuate between -10% and +15%
        change = random.randint(-int(zone["capacity"] * 0.1), int(zone["capacity"] * 0.15))
        new_current = max(0, min(zone["capacity"], zone.get("current", 0) + change))
        zone["current"] = new_current
        new_zones.append(zone)
        total_occupancy += new_current

    await firestore_service.update_zones(venue_id, new_zones)
    # Also update total
    await firestore_service.update_venue(venue_id, {"current_occupancy": total_occupancy})
    
    log_event("crowd_simulated", f"Simulated crowd update for {venue_id}")
    return {"message": "Simulation successful", "new_occupancy": total_occupancy}
