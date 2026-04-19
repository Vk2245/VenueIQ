"""
VenueIQ Data Service (Google Sheets API + SQLite fallback).

Provides database operations using Google Sheets API (via gspread) for
storing venue data, crowd reports, incidents, queue data, and user sessions.
Falls back to an in-memory SQLite database for local development when
Google Sheets credentials are not available.

Google Sheets API is free, requires no GCP billing — only a service
account JSON from Firebase Console (Spark plan, free).
"""

import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from config import settings

# --- Google Sheets Client Singleton ---
_sheets_client: Optional[gspread.Client] = None
_spreadsheet: Optional[gspread.Spreadsheet] = None
_use_local_db: bool = False
_local_db_path: str = "venueiq_local.db"

# Google Sheets API scopes (free, no billing required)
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_sheets_client() -> Optional[gspread.Spreadsheet]:
    """Get or create a singleton Google Sheets client.

    Implements the singleton pattern to reuse the Sheets connection
    across requests. Uses gspread with Google Sheets API v4.

    Returns:
        The gspread Spreadsheet instance, or None if credentials unavailable.
    """
    global _sheets_client, _spreadsheet, _use_local_db

    if _spreadsheet is not None:
        return _spreadsheet

    try:
        if not settings.google_credentials_path or not settings.google_sheets_id:
            raise ValueError("Sheets credentials or ID not configured")

        creds = Credentials.from_service_account_file(
            settings.google_credentials_path,
            scopes=_SCOPES,
        )
        _sheets_client = gspread.authorize(creds)
        _spreadsheet = _sheets_client.open_by_key(settings.google_sheets_id)

        # Ensure required worksheets exist
        _ensure_worksheets(_spreadsheet)

        return _spreadsheet
    except Exception:
        _use_local_db = True
        _init_local_db()
        return None


def _ensure_worksheets(spreadsheet: gspread.Spreadsheet) -> None:
    """Ensure all required worksheets exist in the Google Sheet.

    Creates worksheets with appropriate headers if they don't exist.

    Args:
        spreadsheet: The gspread Spreadsheet instance.
    """
    required_sheets = {
        "venues": ["venue_id", "data", "created_at"],
        "users": ["user_id", "data", "created_at"],
        "sessions": ["token", "user_id", "data", "created_at"],
        "crowd_reports": ["report_id", "venue_id", "data", "created_at"],
        "incidents": ["incident_id", "venue_id", "data", "created_at"],
        "queue_data": ["queue_id", "venue_id", "data", "updated_at"],
    }

    existing = [ws.title for ws in spreadsheet.worksheets()]
    for sheet_name, headers in required_sheets.items():
        if sheet_name not in existing:
            ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
            ws.append_row(headers)


def _get_worksheet(name: str) -> Optional[gspread.Worksheet]:
    """Get a worksheet by name from the spreadsheet.

    Args:
        name: The worksheet name.

    Returns:
        The gspread Worksheet instance, or None.
    """
    spreadsheet = _get_sheets_client()
    if spreadsheet:
        try:
            return spreadsheet.worksheet(name)
        except Exception:
            return None
    return None


def _init_local_db() -> None:
    """Initialize the local SQLite database for development.

    Creates the necessary tables if they don't exist, providing
    a seamless development experience without Google Sheets credentials.
    """
    connection = sqlite3.connect(_local_db_path)
    cursor = connection.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS venues (
            venue_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS crowd_reports (
            report_id TEXT PRIMARY KEY,
            venue_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            venue_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS queue_data (
            queue_id TEXT PRIMARY KEY,
            venue_id TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at REAL NOT NULL
        );
    """)
    connection.commit()
    connection.close()


def _get_local_connection() -> sqlite3.Connection:
    """Get a connection to the local SQLite database.

    Returns:
        SQLite database connection.
    """
    return sqlite3.connect(_local_db_path)


# --- Venue Operations ---

async def create_venue(venue_data: Dict[str, Any]) -> str:
    """Create a new venue record in the database.

    Args:
        venue_data: Dictionary containing venue configuration data.

    Returns:
        The generated unique venue identifier.
    """
    venue_id = f"venue_{uuid.uuid4().hex[:12]}"
    venue_data["venue_id"] = venue_id
    venue_data["created_at"] = time.time()
    venue_data["current_occupancy"] = 0

    ws = _get_worksheet("venues")
    if ws and not _use_local_db:
        ws.append_row([venue_id, json.dumps(venue_data), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO venues (venue_id, data, created_at) VALUES (?, ?, ?)",
            (venue_id, json.dumps(venue_data), time.time()),
        )
        connection.commit()
        connection.close()

    return venue_id


async def get_venue(venue_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a venue by its identifier.

    Args:
        venue_id: The unique venue identifier.

    Returns:
        Venue data dictionary, or None if not found.
    """
    ws = _get_worksheet("venues")
    if ws and not _use_local_db:
        try:
            cell = ws.find(venue_id)
            if cell:
                row = ws.row_values(cell.row)
                return json.loads(row[1]) if len(row) > 1 else None
        except Exception:
            pass
        return None
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT data FROM venues WHERE venue_id = ?", (venue_id,))
        row = cursor.fetchone()
        connection.close()
        if row:
            return json.loads(row[0])
        return None


async def get_demo_venue() -> Dict[str, Any]:
    """Get or create the demo venue for evaluation purposes.

    Provides a pre-configured demo venue (Wankhede Stadium) that
    evaluators can immediately use without any setup.

    Returns:
        Demo venue data dictionary.
    """
    existing = await get_venue("demo-venue")
    if existing:
        return existing

    demo_venue = {
        "venue_id": "demo-venue",
        "name": "Wankhede Stadium",
        "venue_type": "stadium",
        "address": "D Road, Churchgate, Mumbai, Maharashtra 400020",
        "total_capacity": 33000,
        "current_occupancy": 18500,
        "latitude": 18.9389,
        "longitude": 72.8258,
        "zones": [
            {"name": "North Stand", "capacity": 8000, "current": 4200, "zone_type": "seating", "lat": 18.9395, "lng": 72.8258},
            {"name": "South Stand", "capacity": 8000, "current": 5100, "zone_type": "seating", "lat": 18.9383, "lng": 72.8258},
            {"name": "East Pavilion", "capacity": 6000, "current": 3800, "zone_type": "seating", "lat": 18.9389, "lng": 72.8265},
            {"name": "West Terrace", "capacity": 6000, "current": 2900, "zone_type": "seating", "lat": 18.9389, "lng": 72.8251},
            {"name": "Food Court A", "capacity": 2000, "current": 1200, "zone_type": "concession", "lat": 18.9392, "lng": 72.8255},
            {"name": "Food Court B", "capacity": 2000, "current": 800, "zone_type": "concession", "lat": 18.9386, "lng": 72.8261},
            {"name": "Main Entrance", "capacity": 1000, "current": 500, "zone_type": "entry", "lat": 18.9398, "lng": 72.8258},
        ],
        "created_at": time.time(),
    }

    ws = _get_worksheet("venues")
    if ws and not _use_local_db:
        # Check if exists first
        try:
            cell = ws.find("demo-venue")
            if cell:
                ws.update_cell(cell.row, 2, json.dumps(demo_venue))
            else:
                ws.append_row(["demo-venue", json.dumps(demo_venue), time.time()])
        except Exception:
            ws.append_row(["demo-venue", json.dumps(demo_venue), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO venues (venue_id, data, created_at) VALUES (?, ?, ?)",
            ("demo-venue", json.dumps(demo_venue), time.time()),
        )
        connection.commit()
        connection.close()

    return demo_venue

async def update_venue(venue_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates specific fields of an existing venue."""
    venue = await get_venue(venue_id)
    if not venue:
        return False
    
    venue.update(update_data)
    
    ws = _get_worksheet("venues")
    if ws and not _use_local_db:
        try:
            cell = ws.find(venue_id)
            if cell:
                ws.update(f"B{cell.row}", [[json.dumps(venue)]])
                return True
        except Exception:
            pass
        return False
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE venues SET data = ? WHERE venue_id = ?", (json.dumps(venue), venue_id))
        connection.commit()
        connection.close()
        return True

async def update_zones(venue_id: str, zones: List[Dict[str, Any]]) -> bool:
    """Convenience function to specifically update venue zones."""
    return await update_venue(venue_id, {"zones": zones})

# --- User Management ---

async def create_user(user_data: Dict[str, Any]) -> str:
    """Create a new user record.

    Args:
        user_data: Dictionary containing user profile data.

    Returns:
        The generated unique user identifier.
    """
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_data["user_id"] = user_id
    user_data["created_at"] = time.time()

    ws = _get_worksheet("users")
    if ws and not _use_local_db:
        ws.append_row([user_id, json.dumps(user_data), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, data, created_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(user_data), time.time()),
        )
        connection.commit()
        connection.close()

    return user_id


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find a user by their email address.

    Args:
        email: The user's email address.

    Returns:
        User data dictionary, or None if not found.
    """
    ws = _get_worksheet("users")
    if ws and not _use_local_db:
        try:
            records = ws.get_all_values()
            for row in records[1:]:  # Skip header
                if len(row) > 1:
                    user_data = json.loads(row[1])
                    if user_data.get("email") == email:
                        return user_data
        except Exception:
            pass
        return None
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT data FROM users")
        for row in cursor.fetchall():
            user_data = json.loads(row[0])
            if user_data.get("email") == email:
                connection.close()
                return user_data
        connection.close()
        return None


# --- Session Operations ---

async def create_session(token: str, user_id: str, user_data: Dict[str, Any]) -> None:
    """Create a new authentication session.

    Args:
        token: The bearer token for the session.
        user_id: The authenticated user's identifier.
        user_data: Additional session metadata.
    """
    session_data = {
        "token": token,
        "user_id": user_id,
        **user_data,
        "created_at": time.time(),
    }

    ws = _get_worksheet("sessions")
    if ws and not _use_local_db:
        ws.append_row([token[:32], user_id, json.dumps(session_data), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (token, user_id, data, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, json.dumps(session_data), time.time()),
        )
        connection.commit()
        connection.close()


async def validate_session(token: str) -> Optional[Dict[str, Any]]:
    """Validate an authentication token and return session data.

    Args:
        token: The bearer token to validate.

    Returns:
        Session data dictionary, or None if the token is invalid.
    """
    ws = _get_worksheet("sessions")
    if ws and not _use_local_db:
        try:
            cell = ws.find(token[:32])
            if cell:
                row = ws.row_values(cell.row)
                return json.loads(row[2]) if len(row) > 2 else None
        except Exception:
            pass
        return None
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT data FROM sessions WHERE token = ?", (token,))
        row = cursor.fetchone()
        connection.close()
        if row:
            return json.loads(row[0])
        return None


# --- Crowd Reports ---

async def save_crowd_report(report_data: Dict[str, Any]) -> str:
    """Save a crowd density report from an attendee.

    Args:
        report_data: Dictionary containing the crowd observation data.

    Returns:
        The generated unique report identifier.
    """
    report_id = f"report_{uuid.uuid4().hex[:12]}"
    report_data["report_id"] = report_id
    report_data["created_at"] = time.time()

    ws = _get_worksheet("crowd_reports")
    if ws and not _use_local_db:
        ws.append_row([report_id, report_data.get("venue_id", ""), json.dumps(report_data), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO crowd_reports (report_id, venue_id, data, created_at) VALUES (?, ?, ?, ?)",
            (report_id, report_data.get("venue_id", ""), json.dumps(report_data), time.time()),
        )
        connection.commit()
        connection.close()

    return report_id


# --- Incident Operations ---

async def save_incident(incident_data: Dict[str, Any]) -> str:
    """Save a new incident report to the database.

    Args:
        incident_data: Dictionary containing the incident details.

    Returns:
        The generated unique incident identifier.
    """
    incident_id = f"incident_{uuid.uuid4().hex[:12]}"
    incident_data["incident_id"] = incident_id
    incident_data["created_at"] = time.time()

    ws = _get_worksheet("incidents")
    if ws and not _use_local_db:
        ws.append_row([incident_id, incident_data.get("venue_id", ""), json.dumps(incident_data), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO incidents (incident_id, venue_id, data, created_at) VALUES (?, ?, ?, ?)",
            (incident_id, incident_data.get("venue_id", ""), json.dumps(incident_data), time.time()),
        )
        connection.commit()
        connection.close()

    return incident_id


async def get_incidents(venue_id: str) -> List[Dict[str, Any]]:
    """Retrieve all incidents for a venue, sorted by creation time.

    Args:
        venue_id: The venue identifier to filter incidents.

    Returns:
        List of incident data dictionaries.
    """
    ws = _get_worksheet("incidents")
    if ws and not _use_local_db:
        try:
            records = ws.get_all_values()
            incidents = []
            for row in records[1:]:  # Skip header
                if len(row) > 2 and row[1] == venue_id:
                    incidents.append(json.loads(row[2]))
            # Sort by created_at descending
            incidents.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return incidents
        except Exception:
            return []
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT data FROM incidents WHERE venue_id = ? ORDER BY created_at DESC",
            (venue_id,),
        )
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        connection.close()
        return results


async def update_incident(incident_id: str, update_data: Dict[str, Any]) -> bool:
    """Update an existing incident record.

    Args:
        incident_id: The incident identifier to update.
        update_data: Dictionary of fields to update.

    Returns:
        True if the update was successful, False if incident not found.
    """
    ws = _get_worksheet("incidents")
    if ws and not _use_local_db:
        try:
            cell = ws.find(incident_id)
            if not cell:
                return False
            row = ws.row_values(cell.row)
            existing = json.loads(row[2]) if len(row) > 2 else {}
            existing.update(update_data)
            ws.update_cell(cell.row, 3, json.dumps(existing))
            return True
        except Exception:
            return False
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT data FROM incidents WHERE incident_id = ?", (incident_id,))
        row = cursor.fetchone()
        if not row:
            connection.close()
            return False
        existing = json.loads(row[0])
        existing.update(update_data)
        cursor.execute(
            "UPDATE incidents SET data = ? WHERE incident_id = ?",
            (json.dumps(existing), incident_id),
        )
        connection.commit()
        connection.close()
        return True


# --- Queue Operations ---

async def save_queue_data(venue_id: str, queue_data: Dict[str, Any]) -> str:
    """Save or update queue monitoring data.

    Args:
        venue_id: The venue identifier.
        queue_data: Dictionary containing queue status information.

    Returns:
        The queue identifier.
    """
    queue_id = queue_data.get("queue_id", f"queue_{uuid.uuid4().hex[:8]}")
    queue_data["queue_id"] = queue_id
    queue_data["venue_id"] = venue_id
    queue_data["updated_at"] = time.time()

    ws = _get_worksheet("queue_data")
    if ws and not _use_local_db:
        try:
            cell = ws.find(queue_id)
            if cell:
                ws.update_cell(cell.row, 3, json.dumps(queue_data))
                ws.update_cell(cell.row, 4, time.time())
            else:
                ws.append_row([queue_id, venue_id, json.dumps(queue_data), time.time()])
        except Exception:
            ws.append_row([queue_id, venue_id, json.dumps(queue_data), time.time()])
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO queue_data (queue_id, venue_id, data, updated_at) VALUES (?, ?, ?, ?)",
            (queue_id, venue_id, json.dumps(queue_data), time.time()),
        )
        connection.commit()
        connection.close()

    return queue_id


async def get_queue_data(venue_id: str) -> List[Dict[str, Any]]:
    """Retrieve all queue data for a venue.

    Args:
        venue_id: The venue identifier.

    Returns:
        List of queue status dictionaries.
    """
    ws = _get_worksheet("queue_data")
    if ws and not _use_local_db:
        try:
            records = ws.get_all_values()
            results = []
            for row in records[1:]:  # Skip header
                if len(row) > 2 and row[1] == venue_id:
                    results.append(json.loads(row[2]))
            return results
        except Exception:
            return []
    else:
        connection = _get_local_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT data FROM queue_data WHERE venue_id = ?",
            (venue_id,),
        )
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        connection.close()
        return results
