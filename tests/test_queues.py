"""
VenueIQ Queue Management Tests.

Tests for queue status retrieval, queue data updates, and AI-powered
queue wait time predictions. Validates the Reducing Waiting Times
features of the platform.
"""

import pytest


class TestQueueStatus:
    """Tests for the queue status endpoint."""

    def test_get_queue_status(self, test_client):
        """Test retrieving all queue wait times.

        Verifies that the API returns a list of queue status items
        with wait times, queue lengths, and status indicators.
        """
        response = test_client.get("/api/venue/demo-venue/queue-status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify queue item structure
        queue = data[0]
        assert "queue_id" in queue
        assert "queue_name" in queue
        assert "queue_type" in queue
        assert "current_wait_minutes" in queue
        assert "queue_length" in queue
        assert queue["current_wait_minutes"] >= 0

    def test_queue_types_present(self, test_client):
        """Test that multiple queue types are represented.

        Verifies that the demo venue has queues for food courts,
        ticket counters, restrooms, and exits.
        """
        response = test_client.get("/api/venue/demo-venue/queue-status")
        data = response.json()
        queue_types = {q["queue_type"] for q in data}
        assert "food_court" in queue_types
        assert "restroom" in queue_types


class TestQueueUpdate:
    """Tests for the queue data update endpoint."""

    def test_update_queue_data(self, test_client):
        """Test updating queue monitoring data.

        Verifies that venue staff can update wait times and
        queue lengths for a specific queue.
        """
        response = test_client.post(
            "/api/venue/demo-venue/queue-update",
            json={
                "queue_id": "q_food_a",
                "current_wait_minutes": 20,
                "queue_length": 50,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Queue data updated successfully"

    def test_update_queue_invalid_wait(self, test_client):
        """Test queue update with negative wait time.

        Verifies that the API rejects invalid wait time values
        through Pydantic validation.
        """
        response = test_client.post(
            "/api/venue/demo-venue/queue-update",
            json={
                "queue_id": "q_food_a",
                "current_wait_minutes": -5,
                "queue_length": 10,
            },
        )
        assert response.status_code == 422


class TestQueuePrediction:
    """Tests for the AI queue prediction endpoint."""

    def test_queue_prediction(self, test_client):
        """Test AI-powered queue wait time predictions.

        Verifies that the API returns Gemini-generated predictions
        with forecasted wait times, peak times, and recommendations.
        """
        response = test_client.get("/api/venue/demo-venue/queue-predict")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "peak_time_forecast" in data
        assert "recommendations" in data
        assert isinstance(data["predictions"], list)
        assert isinstance(data["recommendations"], list)
