"""
VenueIQ Configuration Module.

Centralizes all application configuration, environment variable loading,
and constants used throughout the VenueIQ platform. Uses python-dotenv
for local development and supports container-based deployment.
"""

import os
from typing import List

from dotenv import load_dotenv

# Load environment variables from .env file (local development)
load_dotenv()


class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        gemini_api_key: Google Gemini API key for AI features.
        google_credentials_path: Path to Firebase/Google service account JSON.
        google_sheets_id: Google Sheets document ID for data persistence.
        firebase_api_key: Firebase web API key.
        firebase_auth_domain: Firebase authentication domain.
        firebase_project_id: Firebase project identifier.
        firebase_storage_bucket: Firebase Cloud Storage bucket.
        firebase_messaging_sender_id: Firebase Cloud Messaging sender ID.
        firebase_app_id: Firebase application identifier.
        firebase_measurement_id: Firebase Analytics measurement ID.
        recaptcha_site_key: Google reCAPTCHA v3 site key.
        recaptcha_secret_key: Google reCAPTCHA v3 secret key.
        app_secret_key: Secret key for token signing.
        app_env: Application environment (development/production).
        cors_origins: Allowed CORS origin domains.
        port: Server port number.
        demo_mode: Whether demo mode is enabled for evaluators.
    """

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # Google Gemini AI Keys (Fallback support)
        # Using a list of keys to automatically rotate on 429 quota exhaustion errors
        self.gemini_api_keys: List[str] = []
        if os.getenv("GEMINI_API_KEY_6104"):
            self.gemini_api_keys.append(os.getenv("GEMINI_API_KEY_6104"))
        if os.getenv("GEMINI_API_KEY"):
            self.gemini_api_keys.append(os.getenv("GEMINI_API_KEY"))
        
        # Keep backwards compatibility for anything looking for singular key
        self.gemini_api_key: str = self.gemini_api_keys[0] if self.gemini_api_keys else ""

        # Google Service Account (free from Firebase Console)
        self.google_credentials_path: str = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )

        # Google Sheets API (free, no billing required)
        self.google_sheets_id: str = os.getenv("GOOGLE_SHEETS_ID", "")

        # Firebase Configuration (Spark plan — free, no billing)
        self.firebase_api_key: str = os.getenv("FIREBASE_API_KEY", "")
        self.firebase_auth_domain: str = os.getenv("FIREBASE_AUTH_DOMAIN", "")
        self.firebase_project_id: str = os.getenv(
            "FIREBASE_PROJECT_ID", "venueiq-demo"
        )
        self.firebase_storage_bucket: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")
        self.firebase_messaging_sender_id: str = os.getenv(
            "FIREBASE_MESSAGING_SENDER_ID", ""
        )
        self.firebase_app_id: str = os.getenv("FIREBASE_APP_ID", "")
        self.firebase_measurement_id: str = os.getenv("FIREBASE_MEASUREMENT_ID", "")

        # Google reCAPTCHA v3 (free, no billing required)
        self.recaptcha_site_key: str = os.getenv("RECAPTCHA_SITE_KEY", "")
        self.recaptcha_secret_key: str = os.getenv("RECAPTCHA_SECRET_KEY", "")

        # Application
        self.app_secret_key: str = os.getenv(
            "APP_SECRET_KEY", "dev-secret-key-change-in-production"
        )
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.cors_origins: List[str] = os.getenv(
            "CORS_ORIGINS", "http://localhost:8000"
        ).split(",")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production mode.

        Returns:
            True if APP_ENV is set to 'production'.
        """
        return self.app_env == "production"


# Singleton settings instance
settings = Settings()

# --- Constants ---

# Rate limiting
RATE_LIMIT_AUTH: int = 10  # Max requests per minute for auth endpoints
RATE_LIMIT_WINDOW: int = 60  # Window in seconds for rate limiting

# Cache TTL
CACHE_TTL_GEMINI: int = 60  # Seconds to cache Gemini responses
CACHE_TTL_QUEUE: int = 30  # Seconds to cache queue predictions
CACHE_TTL_HEATMAP: int = 15  # Seconds to cache heatmap data

# Venue Defaults
MAX_VENUE_ZONES: int = 50  # Maximum zones per venue
MAX_QUEUE_POINTS: int = 100  # Maximum queue monitoring points
MAX_INCIDENT_PHOTO_SIZE: int = 5 * 1024 * 1024  # 5MB max photo upload

# AI Assistant
SUPPORTED_LANGUAGES: List[str] = ["en", "hi"]
DEFAULT_LANGUAGE: str = "en"

# Demo credentials
DEMO_EMAIL: str = "demo@venueiq.com"
DEMO_PASSWORD: str = "demo123"
DEMO_STAFF_NAME: str = "Demo Manager"
