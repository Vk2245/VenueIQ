"""VenueIQ — AI-Powered Smart Venue Intelligence Platform.

Main FastAPI application for VenueIQ, providing AI-powered crowd analytics,
predictive queue management, and smart coordination for physical event venues.
Built for the PromptWars Virtual hackathon (Google H2S / Hack2Skill) addressing
the "Physical Event Experience" challenge.

Features:
    - AI Crowd Density Analysis (Google Gemini 2.5 Flash)
    - Smart Queue Predictor with real-time wait times
    - Real-Time Venue Dashboard for venue managers
    - Bilingual AI Assistant (English/Hindi)
    - Incident Reporting with AI severity assessment
    - Leaflet.js Heatmap visualization (OpenStreetMap)
    - Predictive Analytics for crowd forecasting

Google Services Integration (ALL FREE — no GCP billing):
    - Google Gemini 2.5 Flash (AI engine) — via AI Studio free key
    - Google Sheets API (database via gspread) — free
    - Firebase Admin SDK (authentication) — Spark plan free
    - Firebase Cloud Messaging (push notifications) — Spark plan free
    - Firebase Analytics (frontend tracking) — Spark plan free
    - Firebase Auth JS SDK (Google Sign-In) — Spark plan free
    - Google Fonts (Inter typography) — always free
    - Google reCAPTCHA v3 (form protection) — free
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import firebase_admin
from firebase_admin import credentials

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import analytics, auth, crowd, incidents, queues, venues

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("venueiq")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("🚀 VenueIQ starting up...")

    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(settings.google_credentials_path)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase Admin SDK Initialized")
        except Exception as e:
            logger.warning(f"⚠️ Firebase Admin SDK init skipped: {e}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Demo Mode: {settings.demo_mode}")

    # Initialize demo venue data
    if settings.demo_mode:
        try:
            from services.firestore_service import get_demo_venue
            await get_demo_venue()
            logger.info("✅ Demo venue (Wankhede Stadium) initialized")
        except Exception as error:
            logger.warning(f"Demo venue init skipped: {error}")

    logger.info("✅ VenueIQ ready to serve requests")
    yield

    # Shutdown
    logger.info("👋 VenueIQ shutting down...")


# --- FastAPI Application ---
app = FastAPI(
    title="VenueIQ — AI-Powered Smart Venue Intelligence",
    description=(
        "VenueIQ addresses the PromptWars Virtual challenge of improving the "
        "Physical Event Experience at large-scale venues like stadiums, cinema halls, "
        "metro stations, and concert venues. Powered by Google Gemini 2.5 Flash, "
        "Google Sheets API, Firebase Auth, Analytics, and reCAPTCHA v3."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Register Routers ---
app.include_router(auth.router)
app.include_router(venues.router)
app.include_router(crowd.router)
app.include_router(queues.router)
app.include_router(incidents.router)
app.include_router(analytics.router)

# --- Static Files (Frontend PWA) ---
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Root & Health Endpoints ---

@app.get(
    "/",
    summary="Serve VenueIQ Frontend",
    description="Serves the VenueIQ PWA frontend application.",
    include_in_schema=False,
)
async def root():
    """Redirect root to the VenueIQ frontend application.

    Returns:
        Redirect response to the static frontend.
    """
    from fastapi.responses import FileResponse
    response = FileResponse("static/v10.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get(
    "/health",
    summary="Health Check",
    description="Returns the application health status for monitoring and "
    "load balancer health checks on Google Cloud Run.",
    tags=["System"],
)
async def health_check():
    """Check application health status.

    Used by Google Cloud Run health checks and monitoring systems
    to verify the application is running correctly.

    Returns:
        Dictionary with health status and application metadata.
    """
    return {
        "status": "healthy",
        "service": "VenueIQ",
        "version": "1.0.0",
        "environment": settings.app_env,
        "demo_mode": settings.demo_mode,
    }


@app.get(
    "/api/config/frontend",
    summary="Get Frontend Configuration",
    description="Returns non-sensitive configuration values for the frontend "
    "including Firebase config and reCAPTCHA site key.",
    tags=["System"],
)
async def get_frontend_config():
    """Get frontend configuration for Firebase and reCAPTCHA initialization.

    Returns non-sensitive configuration values needed by the frontend
    JavaScript to initialize Firebase Analytics, Auth, and reCAPTCHA.

    Returns:
        Dictionary with Firebase and reCAPTCHA configuration.
    """
    return {
        "firebase": {
            "apiKey": settings.firebase_api_key,
            "authDomain": settings.firebase_auth_domain,
            "projectId": settings.firebase_project_id,
            "storageBucket": settings.firebase_storage_bucket,
            "messagingSenderId": settings.firebase_messaging_sender_id,
            "appId": settings.firebase_app_id,
            "measurementId": settings.firebase_measurement_id,
        },
        "recaptcha": {
            "siteKey": settings.recaptcha_site_key,
        },
        "demo_mode": settings.demo_mode,
    }
