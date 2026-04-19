"""
VenueIQ Analytics Router.

Handles AI assistant queries, predictive analytics, and crowd forecasting.
Provides bilingual (English/Hindi) AI assistance for attendees and
predictive intelligence for venue managers using Google Gemini.
"""

from typing import Any, Dict

from fastapi import APIRouter

from models import (
    AssistantQuery,
    AssistantResponse,
    PredictionResponse,
)
from services import firestore_service, gemini_service
from services.notification_service import log_event

router = APIRouter(tags=["Analytics & AI Assistant"])


@router.post(
    "/api/ai/assistant",
    response_model=AssistantResponse,
    summary="AI Event Assistant",
    description="Bilingual (English/Hindi) AI chatbot powered by Gemini 2.5 Flash "
    "that helps attendees find nearest exits, shortest queues, facilities, "
    "emergency info, and event schedules. Supports both text and voice input.",
)
async def ai_assistant(query: AssistantQuery) -> AssistantResponse:
    """Process an attendee query through the AI assistant.

    Uses Gemini 2.5 Flash to provide intelligent, context-aware
    responses to attendee questions in English or Hindi. Covers
    navigation, queue information, facilities, and emergency info.

    Args:
        query: Attendee's question with venue context and language preference.

    Returns:
        AssistantResponse with AI-generated answer and suggestions.
    """
    # Get venue context
    venue = await firestore_service.get_venue(query.venue_id)
    venue_name = venue.get("name", "the venue") if venue else "the venue"
    venue_type = venue.get("venue_type", "stadium") if venue else "stadium"
    venue_context = f"{venue_name} ({venue_type})"

    # Get AI response
    result = await gemini_service.ai_assistant_respond(
        query=query.query,
        venue_type=venue_type,
        language=query.language,
        venue_context=venue_context,
    )

    log_event(
        "ai_assistant_query",
        f"AI assistant query in {query.language}: {query.query[:50]}",
        metadata={"venue_id": query.venue_id, "language": query.language},
    )

    return AssistantResponse(
        response=result.get("response", "I'm here to help!"),
        language=query.language,
        suggestions=result.get("suggestions", []),
        relevant_zones=result.get("relevant_zones", []),
    )


@router.get(
    "/api/venue/{venue_id}/analytics",
    response_model=PredictionResponse,
    summary="Predictive Analytics",
    description="Uses historical event data to forecast crowd patterns, "
    "predict peak times, and recommend pre-event logistics adjustments. "
    "Powered by Google Gemini for intelligent forecasting.",
)
async def get_analytics(venue_id: str) -> PredictionResponse:
    """Get predictive crowd analytics for a venue.

    Generates AI-powered crowd forecasts, peak time predictions,
    and logistics recommendations based on historical patterns
    and current event data.

    Args:
        venue_id: The venue identifier.

    Returns:
        PredictionResponse with crowd forecasts and recommendations.
    """
    venue = await firestore_service.get_venue(venue_id)
    venue_type = venue.get("venue_type", "stadium") if venue else "stadium"

    prediction = await gemini_service.generate_predictions(
        venue_type=venue_type,
    )

    log_event(
        "analytics_generated",
        f"Predictive analytics generated for venue {venue_id}",
        metadata={"venue_id": venue_id},
    )

    return PredictionResponse(
        venue_id=venue_id,
        predicted_peak_times=prediction.get("predicted_peak_times", []),
        crowd_forecast=prediction.get("crowd_forecast", []),
        logistics_recommendations=prediction.get("logistics_recommendations", []),
        historical_patterns=prediction.get("historical_patterns", []),
    )


@router.get(
    "/api/venue/{venue_id}/predictions",
    response_model=PredictionResponse,
    summary="Peak Time Forecasts",
    description="Forecast crowd patterns and peak times for upcoming events. "
    "Helps venue managers plan staffing, gate assignments, and concession "
    "operations in advance.",
)
async def get_predictions(venue_id: str) -> PredictionResponse:
    """Get peak time forecasts for a venue event.

    Specialized prediction endpoint focused on peak time windows
    and pre-event logistics planning.

    Args:
        venue_id: The venue identifier.

    Returns:
        PredictionResponse with peak time forecasts.
    """
    venue = await firestore_service.get_venue(venue_id)
    venue_type = venue.get("venue_type", "stadium") if venue else "stadium"

    prediction = await gemini_service.generate_predictions(
        venue_type=venue_type,
    )

    return PredictionResponse(
        venue_id=venue_id,
        predicted_peak_times=prediction.get("predicted_peak_times", []),
        crowd_forecast=prediction.get("crowd_forecast", []),
        logistics_recommendations=prediction.get("logistics_recommendations", []),
        historical_patterns=prediction.get("historical_patterns", []),
    )
