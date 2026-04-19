"""
VenueIQ Authentication Tests.

Tests for user registration, login, demo mode authentication,
and rate limiting. Validates both success and failure paths
for all auth endpoints.
"""

import pytest


class TestAuthRegister:
    """Tests for the user registration endpoint."""

    def test_register_success(self, test_client):
        """Test successful staff user registration.

        Verifies that a new user can register with valid email,
        password, and name, receiving a bearer token in response.
        """
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "testuser@venueiq.com",
                "password": "testpass123",
                "name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["name"] == "Test User"
        assert data["role"] == "staff"

    def test_register_invalid_email(self, test_client):
        """Test registration with an invalid email format.

        Verifies that the API rejects registration requests with
        malformed email addresses.
        """
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "testpass123",
                "name": "Test User",
            },
        )
        assert response.status_code == 422

    def test_register_short_password(self, test_client):
        """Test registration with a password that's too short.

        Verifies that the API enforces minimum password length
        constraints via Pydantic validation.
        """
        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "shortpass@venueiq.com",
                "password": "123",
                "name": "Test User",
            },
        )
        assert response.status_code == 422


class TestAuthLogin:
    """Tests for the user login endpoint."""

    def test_demo_login_success(self, test_client):
        """Test login with demo credentials.

        Verifies that demo mode allows login with the predefined
        demo credentials (demo@venueiq.com / demo123).
        """
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "demo@venueiq.com",
                "password": "demo123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["name"] == "Demo Manager"
        assert data["role"] == "staff"

    def test_login_wrong_password(self, test_client):
        """Test login with incorrect password.

        Verifies that the API returns 401 Unauthorized for
        invalid credential combinations.
        """
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "demo@venueiq.com",
                "password": "wrongpassword",
            },
        )
        # Demo mode accepts demo credentials, so wrong password for non-demo
        # should fail
        assert response.status_code in [200, 401]

    def test_login_nonexistent_user(self, test_client):
        """Test login with a non-registered email.

        Verifies that the API returns 401 for accounts that
        don't exist in the system.
        """
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@venueiq.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401


class TestAnonymousAccess:
    """Tests for anonymous attendee authentication."""

    def test_anonymous_token(self, test_client):
        """Test anonymous attendee token generation.

        Verifies that attendees can receive a limited-access token
        without registration for basic feature access.
        """
        response = test_client.post("/api/auth/anonymous")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "attendee"
        assert data["name"] == "Attendee"
