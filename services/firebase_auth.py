"""
VenueIQ Firebase Authentication Service.

Provides user authentication using Firebase Admin SDK for token
verification and Google Sign-In support. Includes SHA-256 password
hashing for local auth and bearer token management.
"""

import hashlib
import secrets
import time
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import auth, credentials

from config import settings
from services import firestore_service

# --- Firebase Admin Initialization ---
_firebase_app: Optional[firebase_admin.App] = None


def _initialize_firebase() -> Optional[firebase_admin.App]:
    """Initialize the Firebase Admin SDK.

    Uses service account credentials if available, otherwise falls
    back to Application Default Credentials (ADC) for Cloud Run.

    Returns:
        The Firebase Admin App instance, or None if initialization fails.
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        # Try to use existing default app
        _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except ValueError:
        pass

    try:
        if settings.google_credentials_path:
            cred = credentials.Certificate(settings.google_credentials_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(cred, {
                "projectId": settings.firebase_project_id,
            })
        return _firebase_app
    except Exception:
        # Firebase not configured — use local auth fallback
        return None


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a salt.

    Args:
        password: The plain text password to hash.

    Returns:
        The salted SHA-256 hash as a hex string.
    """
    salt = settings.app_secret_key[:16]
    salted = f"{salt}{password}{salt}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its SHA-256 hash.

    Args:
        password: The plain text password to verify.
        hashed: The stored hashed password.

    Returns:
        True if the password matches, False otherwise.
    """
    return _hash_password(password) == hashed


def _generate_token(user_id: str) -> str:
    """Generate a secure bearer token for a user session.

    Args:
        user_id: The user identifier to include in the token.

    Returns:
        A unique bearer token string.
    """
    random_part = secrets.token_hex(32)
    timestamp = str(int(time.time()))
    token_data = f"{user_id}:{timestamp}:{random_part}"
    return hashlib.sha256(token_data.encode("utf-8")).hexdigest()


async def register_user(email: str, password: str, name: str) -> Dict[str, Any]:
    """Register a new staff user.

    Creates the user in the local database with a hashed password
    and optionally in Firebase Auth when credentials are available.

    Args:
        email: The user's email address.
        password: The user's plain text password.
        name: The user's display name.

    Raises:
        ValueError: If the email is already registered.

    Returns:
        Dictionary with user_id, token, and user details.
    """
    # Check for existing user
    existing = await firestore_service.get_user_by_email(email)
    if existing:
        raise ValueError("Email already registered")

    # Hash password
    password_hash = _hash_password(password)

    # Create user in local database
    user_data = {
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "role": "staff",
    }
    user_id = await firestore_service.create_user(user_data)

    # Try to create in Firebase Auth (if available)
    firebase_app = _initialize_firebase()
    if firebase_app:
        try:
            firebase_user = auth.create_user(
                email=email,
                password=password,
                display_name=name,
            )
            user_data["firebase_uid"] = firebase_user.uid
        except Exception:
            pass  # Continue with local auth

    # Generate session token
    token = _generate_token(user_id)
    await firestore_service.create_session(token, user_id, {
        "name": name,
        "email": email,
        "role": "staff",
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "name": name,
        "role": "staff",
    }


async def login_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate a user with email and password.

    Args:
        email: The user's email address.
        password: The user's plain text password.

    Raises:
        ValueError: If credentials are invalid.

    Returns:
        Dictionary with access_token and user details.
    """
    # Check demo credentials
    if settings.demo_mode and email == "demo@venueiq.com" and password == "demo123":
        token = _generate_token("demo-user")
        await firestore_service.create_session(token, "demo-user", {
            "name": "Demo Manager",
            "email": email,
            "role": "staff",
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": "demo-user",
            "name": "Demo Manager",
            "role": "staff",
        }

    # Look up user
    user = await firestore_service.get_user_by_email(email)
    if not user:
        raise ValueError("Invalid email or password")

    # Verify password
    if not _verify_password(password, user.get("password_hash", "")):
        raise ValueError("Invalid email or password")

    # Generate session
    user_id = user["user_id"]
    token = _generate_token(user_id)
    await firestore_service.create_session(token, user_id, {
        "name": user.get("name", ""),
        "email": email,
        "role": user.get("role", "staff"),
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "name": user.get("name", ""),
        "role": user.get("role", "staff"),
    }


async def verify_google_token(id_token: str) -> Dict[str, Any]:
    """Verify a Google Sign-In ID token using Firebase Admin SDK.

    Args:
        id_token: The Firebase ID token from Google Sign-In.

    Raises:
        ValueError: If the token is invalid or Firebase is not configured.

    Returns:
        Dictionary with access_token and user details.
    """
    firebase_app = _initialize_firebase()
    if not firebase_app:
        raise ValueError("Firebase not configured for Google Sign-In")

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "Google User")

        # Check if user exists locally
        user = await firestore_service.get_user_by_email(email)
        if not user:
            user_data = {
                "email": email,
                "name": name,
                "role": "staff",
                "firebase_uid": uid,
                "password_hash": "",
            }
            user_id = await firestore_service.create_user(user_data)
        else:
            user_id = user["user_id"]

        # Generate session
        token = _generate_token(user_id)
        await firestore_service.create_session(token, user_id, {
            "name": name,
            "email": email,
            "role": "staff",
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user_id,
            "name": name,
            "role": "staff",
        }

    except auth.InvalidIdTokenError:
        raise ValueError("Invalid Google Sign-In token")


async def get_anonymous_token() -> Dict[str, Any]:
    """Generate an anonymous attendee token.

    Provides quick access for venue attendees without requiring
    registration, enabling incident reporting and AI assistant usage.

    Returns:
        Dictionary with a limited-access anonymous token.
    """
    anon_id = f"anon_{secrets.token_hex(8)}"
    token = _generate_token(anon_id)
    await firestore_service.create_session(token, anon_id, {
        "name": "Attendee",
        "role": "attendee",
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": anon_id,
        "name": "Attendee",
        "role": "attendee",
    }


async def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a bearer token and return session data.

    Args:
        token: The bearer token to validate.

    Returns:
        Session data dictionary, or None if the token is invalid.
    """
    return await firestore_service.validate_session(token)
