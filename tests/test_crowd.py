"""
VenueIQ Crowd Analysis Tests.

Tests for AI-powered crowd density analysis, heatmap data generation,
and crowd observation reporting. Validates the core Crowd Management
features of the platform.
"""

import pytest


class TestCrowdAnalysis:
    """Tests for the AI crowd density analysis endpoint."""

    def test_crowd_analysis_success(self, test_client):
        """Test successful crowd density analysis.

        Verifies that the API processes a crowd description
        and returns structured analysis results from Gemini AI.
        """
        response = test_client.post(
            "/api/venue/crowd-analysis",
            json={
                "description": "Large crowd near the main entrance, people are moving slowly and there seems to be a bottleneck",
                "venue_id": "demo-venue",
                "zone_name": "Main Entrance",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "density_level" in data
        assert data["density_level"] in ["normal", "busy", "crowded", "critical"]
        assert "estimated_count" in data
        assert "flow_recommendations" in data
        assert "safety_score" in data
        assert isinstance(data["flow_recommendations"], list)

    def test_crowd_analysis_short_description(self, test_client):
        """Test crowd analysis with too-short description.

        Verifies that the API rejects descriptions under the
        minimum character length requirement.
        """
        response = test_client.post(
            "/api/venue/crowd-analysis",
            json={
                "description": "busy",
                "venue_id": "demo-venue",
            },
        )
        assert response.status_code == 422

    def test_crowd_analysis_with_zone(self, test_client):
        """Test crowd analysis with specific zone context.

        Verifies that the analysis includes zone-specific context
        when a zone name is provided.
        """
        response = test_client.post(
            "/api/venue/crowd-analysis",
            json={
                "description": "Food court area is extremely packed during halftime, long queues at all counters",
                "venue_id": "demo-venue",
                "zone_name": "Food Court A",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["venue_id"] == "demo-venue"


class TestHeatmap:
    """Tests for the venue heatmap data endpoint."""

    def test_heatmap_demo_venue(self, test_client):
        """Test heatmap data generation for the demo venue.

        Verifies that the API returns properly formatted heatmap
        data points with GPS coordinates and weights for Google Maps.
        """
        response = test_client.get("/api/venue/demo-venue/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert "data_points" in data
        assert isinstance(data["data_points"], list)
        assert len(data["data_points"]) > 0
        # Verify data point structure
        point = data["data_points"][0]
        assert "latitude" in point
        assert "longitude" in point
        assert "weight" in point
        assert "zone_name" in point
        assert 0.0 <= point["weight"] <= 1.0

    def test_heatmap_invalid_venue(self, test_client):
        """Test heatmap request for a non-existent venue.

        Verifies that the API returns 404 for invalid venue IDs.
        """
        response = test_client.get("/api/venue/nonexistent-venue/heatmap")
        assert response.status_code == 404


class TestCrowdReport:
    """Tests for the crowd observation report endpoint."""

    def test_submit_crowd_report(self, test_client):
        """Test submitting a crowd density observation.

        Verifies that attendees can submit crowd condition reports
        with zone, density estimate, and optional GPS location.
        """
        response = test_client.post(
            "/api/venue/demo-venue/crowd-report",
            json={
                "zone_name": "North Stand",
                "density_estimate": 7,
                "description": "Pretty crowded in the upper sections",
                "latitude": 18.9395,
                "longitude": 72.8258,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert data["venue_id"] == "demo-venue"
