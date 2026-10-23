"""Central settings. Everything you may want to tweak lives here."""

import os
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

UTC = timezone.utc

# Ayan's timezone, and the hours he offers meetings in (his own time)
OWNER_TZ_NAME = "Asia/Karachi"
OWNER_TZ = ZoneInfo(OWNER_TZ_NAME)
DAY_START_HOUR = int(os.getenv("DAY_START_HOUR", "10"))
DAY_END_HOUR = int(os.getenv("DAY_END_HOUR", "22"))

# Meeting rules
SLOT_STEP_MINUTES = 30
MIN_DURATION = 15
MAX_DURATION = 120
MAX_DAYS_AHEAD = 60

# Chat rate limit (per IP)
CHAT_LIMIT = 20
CHAT_WINDOW_SECONDS = 60

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://meetayan.vercel.app",
]

# Google Calendar
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_PATH = Path(os.getenv("GOOGLE_TOKEN_JSON", str(Path(__file__).parent / "google_token.json")))
