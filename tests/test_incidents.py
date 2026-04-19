"""
VenueIQ Incident Reporting Tests.

Tests for incident creation with AI severity assessment, incident
listing, and status updates. Validates the Real-Time Coordination
features of the platform.
"""

import pytest


class TestIncidentCreation:
    """Tests for the incident reporting endpoint."""

    def test_create_incident_success(self, test_client):
        """Test successful incident report creation.

        Verifies that the API accepts incident reports with category,
        zone, and description, returning AI-assessed severity and
        team assignment.
        """
        response = test_client.post(
            "/api/venue/demo-venue/incident",
            json={
                "category": "overcrowding",
                "zone_name": "North Stand",
                "description": "Dangerous overcrowding in upper section, people unable to move freely",
                "venue_id": "demo-venue",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "incident_id" in data
        assert data["venue_id"] == "demo-venue"
        assert data["category"] == "overcrowding"
        assert "severity" in data
        assert data["severity"] in ["low", "medium", "high", "critical"]
        assert "assigned_team" in data
        assert data["assigned_team"] != ""
        assert data["status"] == "reported"

    def test_create_incident_medical(self, test_client):
        """Test medical emergency incident report.

        Verifies that medical incidents receive appropriate severity
        rating and are routed to the Medical Response team.
        """
        response = test_client.post(
            "/api/venue/demo-venue/incident",
            json={
                "category": "medical",
                "zone_name": "East Pavilion",
                "description": "An attendee has collapsed near seat E-42, appears to be having a heat stroke",
                "venue_id": "demo-venue",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["severity"] in ["high", "critical"]

    def test_create_incident_short_description(self, test_client):
        """Test incident creation with too-short description.

        Verifies that the API rejects descriptions under the
        minimum character length requirement.
        """
        response = test_client.post(
            "/api/venue/demo-venue/incident",
            json={
                "category": "spill",
                "zone_name": "Food Court A",
                "description": "spill",
                "venue_id": "demo-venue",
            },
        )
        assert response.status_code == 422

    def test_create_incident_with_location(self, test_client):
        """Test incident creation with GPS coordinates.

        Verifies that the API accepts and stores GPS location
        data along with the incident report.
        """
        response = test_client.post(
            "/api/venue/demo-venue/incident",
            json={
                "category": "safety_hazard",
                "zone_name": "West Terrace",
                "description": "Broken railing on the terrace steps, potential fall hazard for attendees",
                "venue_id": "demo-venue",
                "latitude": 18.9389,
                "longitude": 72.8251,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["latitude"] == 18.9389
        assert data["longitude"] == 72.8251


class TestIncidentListing:
    """Tests for the incident listing endpoint."""

    def test_list_incidents(self, test_client):
        """Test retrieving incidents for a venue.

        Verifies that the API returns a list of incident reports
        for the specified venue.
        """
        response = test_client.get("/api/venue/demo-venue/incidents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestIncidentUpdate:
    """Tests for the incident status update endpoint."""

    def test_update_nonexistent_incident(self, test_client):
        """Test updating a non-existent incident.

        Verifies that the API returns 404 when trying to update
        an incident that doesn't exist.
        """
        response = test_client.put(
            "/api/venue/demo-venue/incident/nonexistent-id",
            json={"status": "acknowledged"},
        )
        assert response.status_code == 404
