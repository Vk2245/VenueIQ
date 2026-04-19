"""
VenueIQ Pydantic Models.

Defines all request/response schemas for the VenueIQ API using Pydantic v2.
Includes input validation, HTML sanitization, and field constraints to ensure
data integrity and security across all endpoints.
"""

import re
import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# --- Utility Functions ---

def strip_html_tags(value: str) -> str:
    """Remove HTML tags from a string to prevent XSS attacks.

    Args:
        value: The input string potentially containing HTML tags.

    Returns:
        The sanitized string with all HTML tags removed.
    """
    clean = re.sub(r"<[^>]+>", "", value)
    return clean.strip()


# --- Enums ---

class VenueType(str, Enum):
    """Supported venue types for the VenueIQ platform."""
    STADIUM = "stadium"
    CINEMA = "cinema"
    METRO = "metro"
    CONCERT = "concert"
    EXHIBITION = "exhibition"
    OTHER = "other"


class ZoneStatus(str, Enum):
    """Current operational status of a venue zone."""
    NORMAL = "normal"
    BUSY = "busy"
    CROWDED = "crowded"
    CRITICAL = "critical"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    """Severity levels for incident reports."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategory(str, Enum):
    """Categories for venue incident reports."""
    OVERCROWDING = "overcrowding"
    SAFETY_HAZARD = "safety_hazard"
    SPILL = "spill"
    MEDICAL = "medical"
    SECURITY = "security"
    EQUIPMENT = "equipment"
    OTHER = "other"


class IncidentStatus(str, Enum):
    """Lifecycle status of an incident report."""
    REPORTED = "reported"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class QueueType(str, Enum):
    """Types of queues tracked in a venue."""
    FOOD_COURT = "food_court"
    TICKET_COUNTER = "ticket_counter"
    RESTROOM = "restroom"
    EXIT = "exit"
    ENTRY = "entry"
    MERCHANDISE = "merchandise"
    OTHER = "other"


# --- Auth Models ---

class UserRegister(BaseModel):
    """Schema for staff user registration.

    Attributes:
        email: Staff member's email address.
        password: Password (minimum 6 characters).
        name: Full name of the staff member.
    """
    email: str = Field(..., min_length=5, max_length=255, examples=["staff@venue.com"])
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., min_length=2, max_length=100, examples=["John Doe"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Validate and sanitize email input."""
        value = strip_html_tags(value).lower()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email format")
        return value

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        """Sanitize name input by stripping HTML tags."""
        return strip_html_tags(value)


class UserLogin(BaseModel):
    """Schema for user login.

    Attributes:
        email: Staff member's email address.
        password: Account password.
    """
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Validate and sanitize email input."""
        return strip_html_tags(value).lower()


class GoogleSignInRequest(BaseModel):
    """Schema for Google Sign-In token verification.

    Attributes:
        id_token: Firebase ID token from Google Sign-In.
    """
    id_token: str = Field(..., min_length=10)


class TokenResponse(BaseModel):
    """Schema for authentication token response.

    Attributes:
        access_token: JWT-like bearer token.
        token_type: Type of token (always 'bearer').
        user_id: Unique user identifier.
        name: User's display name.
        role: User role (staff/attendee).
    """
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    role: str = "staff"


# --- Venue Models ---

class ZoneCreate(BaseModel):
    """Schema for creating a venue zone.

    Attributes:
        name: Zone name (e.g., 'North Gate', 'Food Court A').
        capacity: Maximum capacity of the zone.
        zone_type: Type/category of the zone.
        latitude: GPS latitude coordinate of zone center.
        longitude: GPS longitude coordinate of zone center.
    """
    name: str = Field(..., min_length=1, max_length=100)
    capacity: int = Field(..., ge=1, le=500000)
    zone_type: str = Field(default="general", max_length=50)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        """Sanitize zone name."""
        return strip_html_tags(value)


class VenueCreate(BaseModel):
    """Schema for creating a new venue.

    Attributes:
        name: Venue name.
        venue_type: Type of venue (stadium, cinema, etc.).
        address: Physical address of the venue.
        total_capacity: Maximum total capacity.
        latitude: GPS latitude of venue.
        longitude: GPS longitude of venue.
        zones: List of zone configurations.
    """
    name: str = Field(..., min_length=2, max_length=200, examples=["Wankhede Stadium"])
    venue_type: VenueType = Field(default=VenueType.STADIUM)
    address: str = Field(..., min_length=5, max_length=500)
    total_capacity: int = Field(..., ge=10, le=1000000)
    latitude: float = Field(..., ge=-90, le=90, examples=[19.0448])
    longitude: float = Field(..., ge=-180, le=180, examples=[72.8199])
    zones: List[ZoneCreate] = Field(default_factory=list)

    @field_validator("name", "address")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        """Sanitize text fields."""
        return strip_html_tags(value)


class VenueResponse(BaseModel):
    """Schema for venue data response.

    Attributes:
        venue_id: Unique venue identifier.
        name: Venue name.
        venue_type: Type of venue.
        address: Physical address.
        total_capacity: Maximum capacity.
        current_occupancy: Current number of attendees.
        latitude: GPS latitude.
        longitude: GPS longitude.
        zones: List of zone data.
        created_at: Timestamp of creation.
    """
    venue_id: str
    name: str
    venue_type: str
    address: str
    total_capacity: int
    current_occupancy: int = 0
    latitude: float
    longitude: float
    zones: List[Dict] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


# --- Crowd Models ---

class CrowdAnalysisRequest(BaseModel):
    """Schema for AI crowd density analysis request.

    Attributes:
        venue_id: Target venue for analysis.
        description: Text description of current crowd conditions.
        zone_name: Specific zone to analyze.
        image_base64: Optional base64-encoded photo for visual analysis.
    """
    venue_id: str = Field(default="demo-venue")
    description: str = Field(
        ..., min_length=10, max_length=2000,
        examples=["Large crowd near north gate, movement is slow"]
    )
    zone_name: Optional[str] = Field(default=None, max_length=100)
    image_base64: Optional[str] = Field(default=None)

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, value: str) -> str:
        """Sanitize description text."""
        return strip_html_tags(value)


class CrowdAnalysisResponse(BaseModel):
    """Schema for AI crowd analysis result.

    Attributes:
        venue_id: Venue that was analyzed.
        density_level: Estimated density (normal/busy/crowded/critical).
        estimated_count: Estimated number of people in the zone.
        bottleneck_zones: Identified bottleneck areas.
        flow_recommendations: AI-generated crowd flow suggestions.
        safety_score: Safety score from 1-10.
        analysis_summary: Human-readable analysis summary.
        timestamp: Analysis timestamp.
    """
    venue_id: str
    density_level: str
    estimated_count: int
    bottleneck_zones: List[str] = Field(default_factory=list)
    flow_recommendations: List[str] = Field(default_factory=list)
    safety_score: float = Field(ge=0, le=10)
    analysis_summary: str
    timestamp: float = Field(default_factory=time.time)


class CrowdReportCreate(BaseModel):
    """Schema for attendee crowd density report.

    Attributes:
        zone_name: Name of the zone being reported.
        density_estimate: Attendee's estimate of density (1-10).
        description: Optional text description.
        latitude: Reporter's GPS latitude.
        longitude: Reporter's GPS longitude.
    """
    zone_name: str = Field(..., min_length=1, max_length=100)
    density_estimate: int = Field(..., ge=1, le=10)
    description: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("zone_name")
    @classmethod
    def sanitize_zone(cls, value: str) -> str:
        """Sanitize zone name."""
        return strip_html_tags(value)


class HeatmapDataPoint(BaseModel):
    """Schema for a single heatmap data point.

    Attributes:
        latitude: GPS latitude coordinate.
        longitude: GPS longitude coordinate.
        weight: Density weight (0.0 to 1.0).
        zone_name: Name of the associated zone.
    """
    latitude: float
    longitude: float
    weight: float = Field(ge=0.0, le=1.0)
    zone_name: str


class HeatmapResponse(BaseModel):
    """Schema for venue heatmap data response.

    Attributes:
        venue_id: Venue identifier.
        data_points: List of heatmap data points for Google Maps overlay.
        timestamp: Data generation timestamp.
    """
    venue_id: str
    data_points: List[HeatmapDataPoint] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


# --- Queue Models ---

class QueueStatusItem(BaseModel):
    """Schema for a single queue status entry.

    Attributes:
        queue_id: Unique queue identifier.
        queue_name: Display name of the queue.
        queue_type: Type of queue (food, ticket, restroom, etc.).
        current_wait_minutes: Current estimated wait time in minutes.
        queue_length: Estimated number of people in the queue.
        status: Current queue status.
        zone_name: Zone where the queue is located.
    """
    queue_id: str
    queue_name: str
    queue_type: QueueType
    current_wait_minutes: int = Field(ge=0)
    queue_length: int = Field(ge=0)
    status: ZoneStatus = ZoneStatus.NORMAL
    zone_name: str


class QueueUpdateRequest(BaseModel):
    """Schema for updating queue data.

    Attributes:
        queue_id: Target queue identifier.
        current_wait_minutes: Updated wait time in minutes.
        queue_length: Updated queue length.
    """
    queue_id: str = Field(..., min_length=1)
    current_wait_minutes: int = Field(..., ge=0, le=300)
    queue_length: int = Field(..., ge=0, le=10000)


class QueuePredictionResponse(BaseModel):
    """Schema for AI queue wait time prediction.

    Attributes:
        venue_id: Venue identifier.
        predictions: List of queue predictions with time estimates.
        peak_time_forecast: Predicted peak times for the venue.
        recommendations: AI-generated recommendations for queue management.
        timestamp: Prediction generation timestamp.
    """
    venue_id: str
    predictions: List[Dict] = Field(default_factory=list)
    peak_time_forecast: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


# --- Incident Models ---

class IncidentCreate(BaseModel):
    """Schema for creating a new incident report.

    Attributes:
        venue_id: Venue where the incident occurred.
        category: Category of the incident.
        description: Detailed description of the incident.
        zone_name: Zone where the incident was observed.
        latitude: GPS latitude of the incident.
        longitude: GPS longitude of the incident.
        photo_base64: Optional base64-encoded photo evidence.
    """
    venue_id: str = Field(default="demo-venue")
    category: IncidentCategory = Field(default=IncidentCategory.OTHER)
    description: str = Field(..., min_length=10, max_length=1000)
    zone_name: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    photo_base64: Optional[str] = Field(default=None)
    recaptcha_token: Optional[str] = Field(default=None)

    @field_validator("description", "zone_name")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        """Sanitize text fields."""
        return strip_html_tags(value)


class IncidentResponse(BaseModel):
    """Schema for incident report response.

    Attributes:
        incident_id: Unique incident identifier.
        venue_id: Venue where the incident occurred.
        category: Incident category.
        severity: AI-determined severity level.
        description: Incident description.
        zone_name: Zone of the incident.
        status: Current incident status.
        assigned_team: Recommended staff team for resolution.
        ai_assessment: AI-generated assessment of the incident.
        latitude: GPS latitude.
        longitude: GPS longitude.
        created_at: Timestamp of report creation.
    """
    incident_id: str
    venue_id: str
    category: str
    severity: str
    description: str
    zone_name: str
    status: str = IncidentStatus.REPORTED
    assigned_team: str = ""
    ai_assessment: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: float = Field(default_factory=time.time)


class IncidentUpdateRequest(BaseModel):
    """Schema for updating an incident status.

    Attributes:
        status: New incident status.
        resolution_notes: Optional notes about the resolution.
    """
    status: IncidentStatus
    resolution_notes: Optional[str] = Field(default=None, max_length=500)


# --- AI Assistant Models ---

class AssistantQuery(BaseModel):
    """Schema for AI assistant query (text or voice).

    Attributes:
        query: User's question or request.
        venue_id: Context venue for the query.
        language: Response language preference (en/hi).
        user_location: Optional user location within the venue.
    """
    query: str = Field(..., min_length=1, max_length=1000)
    venue_id: str = Field(default="demo-venue")
    language: str = Field(default="en", pattern="^(en|hi)$")
    user_location: Optional[str] = Field(default=None, max_length=200)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, value: str) -> str:
        """Sanitize query text."""
        return strip_html_tags(value)


class AssistantResponse(BaseModel):
    """Schema for AI assistant response.

    Attributes:
        response: AI-generated response text.
        language: Response language.
        suggestions: Follow-up suggestion prompts.
        relevant_zones: Zones relevant to the query.
        timestamp: Response generation timestamp.
    """
    response: str
    language: str
    suggestions: List[str] = Field(default_factory=list)
    relevant_zones: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


# --- Analytics Models ---

class DashboardData(BaseModel):
    """Schema for the live venue dashboard data.

    Attributes:
        venue_id: Venue identifier.
        venue_name: Venue display name.
        total_capacity: Maximum venue capacity.
        current_occupancy: Current number of attendees.
        occupancy_percentage: Current occupancy as a percentage.
        zone_statuses: Status of each zone.
        active_incidents: Count of unresolved incidents.
        avg_wait_time: Average wait time across all queues.
        crowd_trend: Crowd trend (increasing/stable/decreasing).
        staff_recommendations: AI-generated staff deployment suggestions.
        alerts: Active alerts for the venue.
        timestamp: Dashboard data timestamp.
    """
    venue_id: str
    venue_name: str
    total_capacity: int
    current_occupancy: int
    occupancy_percentage: float = Field(ge=0, le=100)
    zone_statuses: List[Dict] = Field(default_factory=list)
    active_incidents: int = 0
    avg_wait_time: int = 0
    crowd_trend: str = "stable"
    staff_recommendations: List[str] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class PredictionResponse(BaseModel):
    """Schema for predictive analytics data.

    Attributes:
        venue_id: Venue identifier.
        predicted_peak_times: Forecasted peak hour windows.
        crowd_forecast: Predicted crowd levels for upcoming hours.
        logistics_recommendations: Pre-event logistics adjustments.
        historical_patterns: Summary of historical crowd patterns.
        timestamp: Prediction generation timestamp.
    """
    venue_id: str
    predicted_peak_times: List[str] = Field(default_factory=list)
    crowd_forecast: List[Dict] = Field(default_factory=list)
    logistics_recommendations: List[str] = Field(default_factory=list)
    historical_patterns: List[Dict] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
