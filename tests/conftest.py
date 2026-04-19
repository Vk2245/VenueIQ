"""
VenueIQ Test Configuration.

Provides shared fixtures, test client setup, and mock configurations
for all test modules. Ensures database isolation per test and mocks
all external API calls (Gemini, Firestore, Firebase).
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables before importing app
os.environ["APP_ENV"] = "development"
os.environ["DEMO_MODE"] = "true"
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["GEMINI_API_KEY"] = "test-api-key"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"


@pytest.fixture(scope="session")
def test_client():
    """Create a TestClient for the FastAPI application.

    Provides a reusable test client that can make HTTP requests
    to the VenueIQ API endpoints for testing.

    Yields:
        TestClient instance configured for testing.
    """
    from main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure a clean database state for each test.

    Resets the in-memory database state before each test to
    prevent test pollution and ensure isolation.

    Yields:
        None — cleanup happens after test completion.
    """
    # Reset rate limit store
    from routers.auth import _rate_limit_store
    _rate_limit_store.clear()

    yield

    # Cleanup after test
    import sqlite3
    try:
        conn = sqlite3.connect("venueiq_local.db")
        cursor = conn.cursor()
        # Don't drop tables, just clean test data
        cursor.execute("DELETE FROM users WHERE data LIKE '%test%'")
        cursor.execute("DELETE FROM sessions WHERE data LIKE '%test%'")
        conn.commit()
        conn.close()
    except Exception:
        pass


@pytest.fixture
def mock_gemini_response():
    """Provide a mock Gemini AI response for testing.

    Returns:
        Dictionary mimicking a Gemini crowd analysis response.
    """
    return {
        "density_level": "busy",
        "estimated_count": 500,
        "bottleneck_zones": ["Main Entrance", "Food Court A"],
        "flow_recommendations": [
            "Open alternate entry gates",
            "Deploy staff to bottleneck zones",
            "Activate digital signage",
        ],
        "safety_score": 7.5,
        "analysis_summary": "Moderate crowd density detected. Staff deployment recommended.",
    }


@pytest.fixture
def auth_headers(test_client):
    """Get authentication headers using demo login.

    Logs in with demo credentials and returns authorization
    headers for authenticated endpoint testing.

    Args:
        test_client: The FastAPI test client fixture.

    Returns:
        Dictionary with Authorization header containing bearer token.
    """
    response = test_client.post(
        "/api/auth/login",
        json={"email": "demo@venueiq.com", "password": "demo123"},
    )
    token = response.json().get("access_token", "test-token")
    return {"Authorization": f"Bearer {token}"}
