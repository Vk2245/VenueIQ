import gspread
from google.oauth2.service_account import Credentials
import logging
from config import settings

logger = logging.getLogger("venueiq.gspread")

# Scopes required for Google Sheets and Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GSpreadService:
    def __init__(self):
        self.enabled = False
        self.client = None
        self.sheet_id = settings.google_sheets_id
        
        try:
            # Attempt to use the same Firebase credentials for Sheets
            creds = Credentials.from_service_account_file(
                settings.google_credentials_path, 
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            self.enabled = True
            logger.info("✅ Google Sheets Service Initialized")
        except Exception as e:
            logger.warning(f"⚠️ Google Sheets Service disabled: {e}")

    async def log_incident(self, incident_data: dict):
        """Logs a new incident to the configured Google Sheet."""
        if not self.enabled or not self.sheet_id:
            logger.info(f"Sheet Sync (Mock): {incident_data.get('title')}")
            return
            
        try:
            sheet = self.client.open_by_key(self.sheet_id).sheet1
            # Row format: [ID, TITLE, CATEGORY, SEVERITY, STATUS, TIMESTAMP]
            row = [
                incident_data.get("id"),
                incident_data.get("title"),
                incident_data.get("category"),
                incident_data.get("severity"),
                incident_data.get("status"),
                incident_data.get("timestamp")
            ]
            sheet.append_row(row)
            logger.info("✅ Incident synced to Google Sheets")
        except Exception as e:
            logger.error(f"❌ Failed to sync to Google Sheets: {e}")

# Singleton instance
gspread_service = GSpreadService()
