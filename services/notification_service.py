"""
VenueIQ Notification Service.

Handles push notifications to venue staff and attendees using Firebase
Cloud Messaging (FCM). Uses Python's built-in logging module for
structured application logging throughout the platform.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import messaging

from config import settings

# --- Structured Logging Setup ---
_logger = logging.getLogger("venueiq.notifications")


def log_event(
    event_type: str,
    message: str,
    severity: str = "INFO",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a structured event using Python logging.

    Provides structured, JSON-compatible log output for monitoring
    and debugging. Compatible with Google Cloud Run log aggregation.

    Args:
        event_type: Type of event (e.g., 'incident_created', 'crowd_alert').
        message: Human-readable log message.
        severity: Log severity level (INFO, WARNING, ERROR, CRITICAL).
        metadata: Optional additional metadata to include in the log entry.
    """
    log_data = {
        "event_type": event_type,
        "message": message,
        "timestamp": time.time(),
        "environment": settings.app_env,
    }
    if metadata:
        log_data["metadata"] = metadata

    log_level = getattr(logging, severity.upper(), logging.INFO)
    _logger.log(log_level, f"[{event_type}] {message} | {metadata}")


# --- Push Notifications ---

async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> bool:
    """Send a push notification to a specific device.

    Uses Firebase Cloud Messaging to deliver real-time alerts to
    venue staff or attendees about crowd conditions, incidents, etc.

    Args:
        token: The FCM device registration token.
        title: Notification title text.
        body: Notification body text.
        data: Optional custom data payload.

    Returns:
        True if the notification was sent successfully.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        log_event(
            "push_notification_sent",
            f"Notification sent: {title}",
            metadata={"response_id": response},
        )
        return True
    except Exception as error:
        log_event(
            "push_notification_error",
            f"Failed to send notification: {str(error)}",
            severity="ERROR",
        )
        return False


async def send_topic_notification(
    topic: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> bool:
    """Send a notification to all subscribers of a topic.

    Used for venue-wide alerts such as crowd surge warnings,
    gate changes, or event schedule updates.

    Args:
        topic: The FCM topic name (e.g., 'venue_demo-venue_alerts').
        title: Notification title text.
        body: Notification body text.
        data: Optional custom data payload.

    Returns:
        True if the notification was sent successfully.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            topic=topic,
        )
        response = messaging.send(message)
        log_event(
            "topic_notification_sent",
            f"Topic notification sent to '{topic}': {title}",
            metadata={"response_id": response},
        )
        return True
    except Exception as error:
        log_event(
            "topic_notification_error",
            f"Failed to send topic notification: {str(error)}",
            severity="ERROR",
        )
        return False


async def send_crowd_alert(
    venue_id: str,
    alert_type: str,
    zone_name: str,
    message: str,
) -> bool:
    """Send a crowd management alert notification.

    Specialized notification for crowd-related events including
    surge warnings, capacity alerts, and zone status changes.

    Args:
        venue_id: The venue identifier for topic routing.
        alert_type: Type of alert (surge_warning, capacity_alert, etc.).
        zone_name: The zone triggering the alert.
        message: Alert message text.

    Returns:
        True if the alert was sent successfully.
    """
    topic = f"venue_{venue_id}_crowd"
    title_map = {
        "surge_warning": "⚠️ Crowd Surge Warning",
        "capacity_alert": "🔴 Zone Capacity Alert",
        "gate_change": "🚪 Gate Change Notice",
        "event_delay": "⏰ Event Delay Notice",
        "amenity_update": "ℹ️ Amenity Update",
    }
    title = title_map.get(alert_type, "📢 Venue Alert")

    log_event(
        "crowd_alert",
        f"Crowd alert for venue {venue_id}: {alert_type} in {zone_name}",
        severity="WARNING",
        metadata={"venue_id": venue_id, "zone_name": zone_name, "alert_type": alert_type},
    )

    return await send_topic_notification(
        topic=topic,
        title=title,
        body=f"{zone_name}: {message}",
        data={
            "alert_type": alert_type,
            "venue_id": venue_id,
            "zone_name": zone_name,
        },
    )


async def notify_incident_team(
    venue_id: str,
    incident_id: str,
    severity: str,
    assigned_team: str,
    zone_name: str,
    description: str,
) -> bool:
    """Send an incident notification to the assigned staff team.

    Routes incident alerts to the correct response team based on
    AI-determined severity and category.

    Args:
        venue_id: The venue identifier.
        incident_id: The incident identifier for reference.
        severity: Incident severity level.
        assigned_team: The team assigned to handle the incident.
        zone_name: Zone where the incident was reported.
        description: Brief incident description.

    Returns:
        True if the notification was sent successfully.
    """
    severity_emoji = {
        "low": "🟡",
        "medium": "🟠",
        "high": "🔴",
        "critical": "🚨",
    }
    emoji = severity_emoji.get(severity, "📢")
    topic = f"venue_{venue_id}_staff_{assigned_team.lower().replace(' ', '_')}"

    log_event(
        "incident_notification",
        f"Incident {incident_id} assigned to {assigned_team}",
        severity="WARNING" if severity in ["high", "critical"] else "INFO",
        metadata={
            "incident_id": incident_id,
            "severity": severity,
            "team": assigned_team,
            "zone": zone_name,
        },
    )

    return await send_topic_notification(
        topic=topic,
        title=f"{emoji} {severity.upper()} Incident — {zone_name}",
        body=f"[{assigned_team}] {description[:100]}",
        data={
            "incident_id": incident_id,
            "severity": severity,
            "zone_name": zone_name,
        },
    )


def get_notification_topics(venue_id: str) -> List[str]:
    """Get all notification topics for a venue.

    Args:
        venue_id: The venue identifier.

    Returns:
        List of FCM topic names for the venue.
    """
    return [
        f"venue_{venue_id}_alerts",
        f"venue_{venue_id}_crowd",
        f"venue_{venue_id}_incidents",
        f"venue_{venue_id}_staff_security",
        f"venue_{venue_id}_staff_medical_response",
        f"venue_{venue_id}_staff_maintenance",
        f"venue_{venue_id}_staff_crowd_control",
    ]
