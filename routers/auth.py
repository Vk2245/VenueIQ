"""
VenueIQ Authentication Router.

Handles user registration, login, Google Sign-In verification, and
anonymous attendee authentication. Implements rate limiting to prevent
brute-force attacks on authentication endpoints.
"""

import time
from typing import Dict

from fastapi import APIRouter, HTTPException, status

from models import (
    GoogleSignInRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from services import firebase_auth
from services.notification_service import log_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# --- Rate Limiting ---
_rate_limit_store: Dict[str, list] = {}
RATE_LIMIT_MAX: int = 10
RATE_LIMIT_WINDOW: int = 60


def _check_rate_limit(client_ip: str) -> bool:
    """Check if a client has exceeded the rate limit.

    Implements a sliding window rate limiter for authentication
    endpoints to prevent brute-force attacks.

    Args:
        client_ip: The client's IP address identifier.

    Returns:
        True if the request is allowed, False if rate limited.
    """
    current_time = time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # Remove expired timestamps
    _rate_limit_store[client_ip] = [
        timestamp for timestamp in _rate_limit_store[client_ip]
        if current_time - timestamp < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        return False

    _rate_limit_store[client_ip].append(current_time)
    return True


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new staff account",
    description="Creates a new venue staff account with email and password. "
    "Returns a bearer token for subsequent authenticated requests.",
)
async def register(user_data: UserRegister) -> TokenResponse:
    """Register a new staff user for venue management.

    Creates the user account with hashed password storage and
    generates an authentication token for immediate use.

    Args:
        user_data: Registration data including email, password, and name.

    Returns:
        TokenResponse with access token and user details.

    Raises:
        HTTPException: 429 if rate limited, 400 if email already exists.
    """
    if not _check_rate_limit(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )

    try:
        result = await firebase_auth.register_user(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
        )
        log_event("user_registered", f"New user registered: {user_data.email}")
        return TokenResponse(**result)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="Authenticates a staff user and returns a bearer token. "
    "Demo credentials: demo@venueiq.com / demo123",
)
async def login(user_data: UserLogin) -> TokenResponse:
    """Authenticate a user with email and password.

    Supports both registered users and demo mode credentials
    for hackathon evaluators.

    Args:
        user_data: Login credentials (email and password).

    Returns:
        TokenResponse with access token and user details.

    Raises:
        HTTPException: 429 if rate limited, 401 if credentials invalid.
    """
    if not _check_rate_limit(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    try:
        result = await firebase_auth.login_user(
            email=user_data.email,
            password=user_data.password,
        )
        log_event("user_login", f"User logged in: {user_data.email}")
        return TokenResponse(**result)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in with Google",
    description="Verifies a Google Sign-In ID token via Firebase Admin SDK.",
)
async def google_sign_in(request: GoogleSignInRequest) -> TokenResponse:
    """Authenticate using Google Sign-In via Firebase.

    Verifies the Firebase ID token and creates a local session
    for the authenticated Google user.

    Args:
        request: Request containing the Firebase ID token.

    Returns:
        TokenResponse with access token and user details.

    Raises:
        HTTPException: 401 if the token is invalid.
    """
    try:
        result = await firebase_auth.verify_google_token(request.id_token)
        log_event("google_sign_in", "User authenticated via Google Sign-In")
        return TokenResponse(**result)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )


@router.post(
    "/anonymous",
    response_model=TokenResponse,
    summary="Get anonymous attendee access",
    description="Generates a limited-access token for venue attendees "
    "without requiring registration. Enables incident reporting and AI assistant.",
)
async def anonymous_access() -> TokenResponse:
    """Generate an anonymous token for venue attendees.

    Provides quick access for attendees to use core features
    like the AI assistant and incident reporting without registration.

    Returns:
        TokenResponse with a limited-access anonymous bearer token.
    """
    result = await firebase_auth.get_anonymous_token()
    log_event("anonymous_access", "Anonymous attendee token generated")
    return TokenResponse(**result)
