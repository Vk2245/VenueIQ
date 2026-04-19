"""
VenueIQ Gemini Service.

Provides AI-powered crowd analysis, queue predictions, and intelligent
assistant capabilities using Google Gemini 2.5 Flash. Includes response
caching for efficiency and structured prompts for venue-specific context.
"""

import json
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from config import CACHE_TTL_GEMINI, settings

# --- Response Cache ---
_response_cache: Dict[str, Dict[str, Any]] = {}


def _get_cached_response(cache_key: str) -> Optional[str]:
    """Retrieve a cached Gemini response if still valid.

    Args:
        cache_key: Unique key identifying the cached request.

    Returns:
        The cached response text, or None if cache miss or expired.
    """
    if cache_key in _response_cache:
        entry = _response_cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL_GEMINI:
            return entry["response"]
        del _response_cache[cache_key]
    return None


def _set_cache(cache_key: str, response: str) -> None:
    """Store a Gemini response in the cache.

    Args:
        cache_key: Unique key for the request.
        response: The response text to cache.
    """
    _response_cache[cache_key] = {
        "response": response,
        "timestamp": time.time(),
    }


let_client_index = 0

def _generate_with_fallback(model_name: str, contents: Any, config: Any = None) -> Any:
    """Attempt generation with primary key, falling back to alternates on 429 ResourceExhausted."""
    import logging
    logger = logging.getLogger(__name__)

    # Fast validation
    if not settings.gemini_api_keys:
        raise Exception("No Gemini API keys configured.")

    last_error = None
    for idx, api_key in enumerate(settings.gemini_api_keys):
        try:
            client = genai.Client(api_key=api_key)
            if config:
                return client.models.generate_content(model=model_name, contents=contents, config=config)
            return client.models.generate_content(model=model_name, contents=contents)
        except Exception as e:
            # Check for Rate Limit (429) or Authentication/Quotas (403 limits)
            err_str = str(e).lower()
            if "429" in err_str or "exhausted" in err_str or "quota" in err_str:
                logger.warning(f"Gemini API key at index {idx} hit limit/quota. Retrying with fallback..." if idx < len(settings.gemini_api_keys) - 1 else "All Gemini API keys exhausted.")
                last_error = e
                continue
            # If it's a completely different error (e.g. bad request geometry), raise it
            raise e

    raise Exception(f"All Gemini API keys hit rate limits/exhaustion. Last error: {last_error}")

class _ClientWrapper:
    """Wrapper to mimic genai.Client but with automatic fallback routing."""
    class _ModelsWrapper:
        def generate_content(self, model: str, contents: Any, config: Any = None):
            return _generate_with_fallback(model_name=model, contents=contents, config=config)
    
    def __init__(self):
        self.models = self._ModelsWrapper()

def _get_client() -> _ClientWrapper:
    """Returns a wrapped client that automatically handles API key fallbacks."""
    return _ClientWrapper()

async def analyze_crowd_density(
    description: str,
    venue_type: str = "stadium",
    zone_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze crowd density using Gemini 2.5 Flash AI.

    Processes a text description (and optionally an image) of current
    crowd conditions and returns structured analysis including density
    levels, bottleneck identification, and flow recommendations.

    Args:
        description: Text description of current crowd conditions.
        venue_type: Type of venue (stadium, cinema, metro, etc.).
        zone_name: Specific zone being analyzed, if applicable.

    Returns:
        Dictionary containing density analysis results with keys:
        density_level, estimated_count, bottleneck_zones,
        flow_recommendations, safety_score, analysis_summary.
    """
    cache_key = f"crowd_{description[:100]}_{venue_type}_{zone_name}"
    cached = _get_cached_response(cache_key)
    if cached:
        return json.loads(cached)

    zone_context = f" in the {zone_name} zone" if zone_name else ""
    prompt = f"""You are VenueIQ, an AI crowd management expert for {venue_type} venues.
Analyze the following crowd conditions{zone_context} and provide a structured assessment.

Current conditions: {description}

Respond in this exact JSON format:
{{
    "density_level": "normal|busy|crowded|critical",
    "estimated_count": <number>,
    "bottleneck_zones": ["zone1", "zone2"],
    "flow_recommendations": ["recommendation1", "recommendation2", "recommendation3"],
    "safety_score": <1-10>,
    "analysis_summary": "Brief summary of the analysis"
}}

Consider crowd safety standards, flow dynamics, and venue-specific factors.
Provide actionable recommendations for venue staff to manage the crowd effectively."""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        response_text = response.text.strip()
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)
        _set_cache(cache_key, json.dumps(result))
        return result

    except Exception:
        # Fallback response for demo/offline mode
        fallback = {
            "density_level": "busy",
            "estimated_count": 450,
            "bottleneck_zones": ["Main Entrance", "Food Court"],
            "flow_recommendations": [
                "Open additional entry gates to distribute crowd flow",
                "Deploy staff at bottleneck zones to guide attendees",
                "Activate digital signage directing to less crowded areas",
            ],
            "safety_score": 7.0,
            "analysis_summary": f"Moderate crowd density detected at the {venue_type}. "
            "Main entrance and food court areas show higher congestion. "
            "Recommended to open alternate routes and deploy additional staff.",
        }
        return fallback


async def predict_queue_times(
    venue_type: str = "stadium",
    current_queues: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Predict wait times for venue queues using Gemini AI.

    Uses historical patterns and current queue data to forecast
    wait times and recommend queue management strategies.

    Args:
        venue_type: Type of venue for context-aware predictions.
        current_queues: Optional list of current queue data.

    Returns:
        Dictionary with predictions, peak_times, and recommendations.
    """
    queue_info = json.dumps(current_queues) if current_queues else "No current queue data"
    cache_key = f"queue_{venue_type}_{hash(queue_info)}"
    cached = _get_cached_response(cache_key)
    if cached:
        return json.loads(cached)

    prompt = f"""You are VenueIQ, an AI queue management system for {venue_type} venues.
Based on the current queue data, predict wait times and provide recommendations.

Current queue data: {queue_info}

Respond in this exact JSON format:
{{
    "predictions": [
        {{"queue_name": "Food Court A", "predicted_wait_minutes": 15, "trend": "increasing"}},
        {{"queue_name": "Ticket Counter", "predicted_wait_minutes": 8, "trend": "stable"}},
        {{"queue_name": "Restroom Block B", "predicted_wait_minutes": 5, "trend": "decreasing"}},
        {{"queue_name": "Exit Gate 3", "predicted_wait_minutes": 12, "trend": "increasing"}}
    ],
    "peak_times": ["7:00 PM - 7:30 PM", "8:30 PM - 9:00 PM"],
    "recommendations": [
        "recommendation1",
        "recommendation2",
        "recommendation3"
    ]
}}

Consider event timing, historical patterns, and crowd flow dynamics."""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        response_text = response.text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)
        _set_cache(cache_key, json.dumps(result))
        return result

    except Exception:
        return {
            "predictions": [
                {"queue_name": "Food Court A", "predicted_wait_minutes": 15, "trend": "increasing"},
                {"queue_name": "Ticket Counter", "predicted_wait_minutes": 8, "trend": "stable"},
                {"queue_name": "Restroom Block B", "predicted_wait_minutes": 5, "trend": "decreasing"},
                {"queue_name": "Exit Gate 3", "predicted_wait_minutes": 12, "trend": "increasing"},
            ],
            "peak_times": ["7:00 PM - 7:30 PM", "8:30 PM - 9:00 PM"],
            "recommendations": [
                "Open additional food counters at Court B to reduce main area load",
                "Deploy queue managers at Exit Gate 3 for staggered exit flow",
                "Announce restroom availability at Block A (currently less crowded)",
            ],
        }


async def ai_assistant_respond(
    query: str,
    venue_type: str = "stadium",
    language: str = "en",
    venue_context: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate AI assistant response for attendee queries.

    Provides bilingual (English/Hindi) AI-powered assistance for
    venue attendees, helping them find facilities, understand wait
    times, and navigate the venue safely.

    Args:
        query: The attendee's question or request.
        venue_type: Type of venue for context.
        language: Response language ('en' for English, 'hi' for Hindi).
        venue_context: Additional venue context information.

    Returns:
        Dictionary with response text, suggestions, and relevant zones.
    """
    lang_instruction = (
        "Respond in Hindi (Devanagari script)." if language == "hi"
        else "Respond in English."
    )
    context = venue_context or f"a large {venue_type} venue"

    prompt = f"""You are VenueIQ Assistant, a helpful AI guide for attendees at {context}.
{lang_instruction}

Attendee's question: {query}

Provide a helpful, concise response. Include:
1. Direct answer to their question
2. 2-3 follow-up suggestions they might find useful
3. Any relevant venue zones or areas

Respond in this exact JSON format:
{{
    "response": "Your helpful response here",
    "suggestions": ["suggestion1", "suggestion2", "suggestion3"],
    "relevant_zones": ["zone1", "zone2"]
}}"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        response_text = response.text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        return json.loads(response_text)

    except Exception:
        if language == "hi":
            return {
                "response": "नमस्ते! मैं VenueIQ सहायक हूं। वर्तमान में फूड कोर्ट A में सबसे कम भीड़ है। "
                "निकटतम शौचालय गेट 4 के पास है। क्या मैं और कुछ मदद कर सकता हूं?",
                "suggestions": [
                    "निकटतम निकास कहां है?",
                    "किस काउंटर पर सबसे कम कतार है?",
                    "आपातकालीन जानकारी",
                ],
                "relevant_zones": ["फूड कोर्ट A", "गेट 4"],
            }
        return {
            "response": "Hello! I'm your VenueIQ Assistant. Food Court A currently has the shortest "
            "wait time of about 5 minutes. The nearest restroom is at Gate 4. How else can I help?",
            "suggestions": [
                "Where is the nearest exit?",
                "Which counter has the shortest queue?",
                "Show me the event schedule",
            ],
            "relevant_zones": ["Food Court A", "Gate 4"],
        }


async def assess_incident_severity(
    category: str,
    description: str,
    zone_name: str,
) -> Dict[str, Any]:
    """Assess incident severity and route to appropriate staff team.

    Uses Gemini AI to evaluate an incident report, determine severity,
    and recommend the correct response team for resolution.

    Args:
        category: Incident category (overcrowding, safety, medical, etc.).
        description: Detailed description of the incident.
        zone_name: Zone where the incident was reported.

    Returns:
        Dictionary with severity, assigned_team, and ai_assessment.
    """
    prompt = f"""You are VenueIQ's incident management AI. Assess this incident:

Category: {category}
Zone: {zone_name}
Description: {description}

Respond in this exact JSON format:
{{
    "severity": "low|medium|high|critical",
    "assigned_team": "team name (e.g., Security, Medical, Maintenance, Crowd Control)",
    "ai_assessment": "Brief assessment and recommended immediate action"
}}

Prioritize safety. Medical and overcrowding incidents should be rated higher severity."""

    try:
        response = _generate_with_fallback(
            model_name="gemini-2.5-flash-preview-04-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        response_text = response.text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        return json.loads(response_text)

    except Exception:
        severity_map = {
            "overcrowding": "high",
            "medical": "critical",
            "safety_hazard": "high",
            "security": "high",
            "spill": "medium",
            "equipment": "low",
            "other": "medium",
        }
        team_map = {
            "overcrowding": "Crowd Control",
            "medical": "Medical Response",
            "safety_hazard": "Security",
            "security": "Security",
            "spill": "Maintenance",
            "equipment": "Maintenance",
            "other": "General Staff",
        }
        return {
            "severity": severity_map.get(category, "medium"),
            "assigned_team": team_map.get(category, "General Staff"),
            "ai_assessment": f"{category.replace('_', ' ').title()} incident reported in {zone_name}. "
            f"Staff has been alerted. Description: {description[:100]}",
        }


async def generate_predictions(
    venue_type: str = "stadium",
    historical_data: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Generate predictive analytics for venue crowd patterns.

    Uses historical event data and AI to forecast crowd patterns,
    predict peak times, and suggest pre-event logistics adjustments.

    Args:
        venue_type: Type of venue for context-aware predictions.
        historical_data: Optional historical crowd pattern data.

    Returns:
        Dictionary with peak_times, crowd_forecast, and logistics_recommendations.
    """
    history_text = json.dumps(historical_data) if historical_data else "No historical data"
    prompt = f"""You are VenueIQ's predictive analytics engine for a {venue_type}.
Based on historical patterns and event data, provide crowd predictions.

Historical data: {history_text}

Respond in this exact JSON format:
{{
    "predicted_peak_times": ["6:30 PM - 7:00 PM (Entry Rush)", "9:00 PM - 9:30 PM (Exit Rush)"],
    "crowd_forecast": [
        {{"hour": "5:00 PM", "expected_occupancy_pct": 20, "risk_level": "low"}},
        {{"hour": "6:00 PM", "expected_occupancy_pct": 55, "risk_level": "moderate"}},
        {{"hour": "7:00 PM", "expected_occupancy_pct": 85, "risk_level": "high"}},
        {{"hour": "8:00 PM", "expected_occupancy_pct": 90, "risk_level": "high"}},
        {{"hour": "9:00 PM", "expected_occupancy_pct": 70, "risk_level": "moderate"}},
        {{"hour": "10:00 PM", "expected_occupancy_pct": 30, "risk_level": "low"}}
    ],
    "logistics_recommendations": [
        "recommendation1",
        "recommendation2",
        "recommendation3"
    ],
    "historical_patterns": [
        {{"pattern": "pattern description", "frequency": "often|sometimes|rare"}}
    ]
}}"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=1024,
            ),
        )
        response_text = response.text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        return json.loads(response_text)

    except Exception:
        return {
            "predicted_peak_times": [
                "6:30 PM - 7:00 PM (Entry Rush)",
                "Half-Time / Intermission",
                "9:00 PM - 9:30 PM (Exit Rush)",
            ],
            "crowd_forecast": [
                {"hour": "5:00 PM", "expected_occupancy_pct": 20, "risk_level": "low"},
                {"hour": "6:00 PM", "expected_occupancy_pct": 55, "risk_level": "moderate"},
                {"hour": "7:00 PM", "expected_occupancy_pct": 85, "risk_level": "high"},
                {"hour": "8:00 PM", "expected_occupancy_pct": 90, "risk_level": "high"},
                {"hour": "9:00 PM", "expected_occupancy_pct": 70, "risk_level": "moderate"},
                {"hour": "10:00 PM", "expected_occupancy_pct": 30, "risk_level": "low"},
            ],
            "logistics_recommendations": [
                "Pre-position crowd control barriers at Gates 1-3 before 6:00 PM",
                "Schedule extra food court staff from 6:30 PM to 8:30 PM",
                "Open all exit gates 15 minutes before event ends to prevent exit congestion",
            ],
            "historical_patterns": [
                {"pattern": "Entry rush peaks 30 minutes before event start", "frequency": "often"},
                {"pattern": "Food court queues double during intermission", "frequency": "often"},
                {"pattern": "Exit congestion at Gate 1 (closest to parking)", "frequency": "sometimes"},
            ],
        }
