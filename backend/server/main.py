import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi import Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agents.graph import ayan_agent

load_dotenv()

app = FastAPI(
    title="Ayan AI Portfolio API",
    description="Backend API for Ayan's AI portfolio assistant.",
    version="1.2.0",
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://meetayan.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
UTC = dt_timezone.utc
OWNER_TZ_NAME = "Asia/Karachi"
OWNER_TZ = ZoneInfo(OWNER_TZ_NAME)
DAY_START_HOUR = int(os.getenv("DAY_START_HOUR", "10"))  # first slot offered (Karachi time)
DAY_END_HOUR = int(os.getenv("DAY_END_HOUR", "22"))      # meetings must end by this hour (Karachi time)
SLOT_STEP_MINUTES = 30
MIN_DURATION = 15
MAX_DURATION = 120
MAX_DAYS_AHEAD = 60
CHAT_LIMIT = 20           # max chat requests per IP...
CHAT_WINDOW_SECONDS = 60  # ...per this many seconds

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BOOKING_LOCK = threading.Lock()  # stops two simultaneous bookings taking the same slot


# ---------------------------------------------------------------------------
# Timezone resolution: "Istanbul" -> Europe/Istanbul, "GMT+5" -> Etc/GMT-5
# ---------------------------------------------------------------------------
_CONTINENTS = (
    "Africa/", "America/", "Antarctica/", "Arctic/", "Asia/",
    "Atlantic/", "Australia/", "Europe/", "Indian/", "Pacific/",
)
_ZONE_BY_LOWER: dict[str, str] = {}
_ZONE_BY_CITY: dict[str, str] = {}
for _z in sorted(available_timezones()):
    if not _z.startswith(_CONTINENTS):
        continue
    _ZONE_BY_LOWER[_z.lower()] = _z
    _ZONE_BY_CITY.setdefault(_z.split("/")[-1].replace("_", " ").lower(), _z)

# Cities that are not IANA names, plus countries that have a single timezone.
# Countries with several zones (USA, Canada, Australia, Brazil, Russia...) are
# intentionally missing, so the assistant asks for the city instead.
_ALIASES = {
    # Pakistan
    "pakistan": "Asia/Karachi", "lahore": "Asia/Karachi", "islamabad": "Asia/Karachi",
    "rawalpindi": "Asia/Karachi", "faisalabad": "Asia/Karachi", "multan": "Asia/Karachi",
    "peshawar": "Asia/Karachi", "quetta": "Asia/Karachi", "sialkot": "Asia/Karachi",
    # India
    "india": "Asia/Kolkata", "delhi": "Asia/Kolkata", "new delhi": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata", "bombay": "Asia/Kolkata", "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata", "chennai": "Asia/Kolkata", "pune": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata", "ahmedabad": "Asia/Kolkata",
    # Middle East
    "turkey": "Europe/Istanbul", "turkiye": "Europe/Istanbul", "istanbul": "Europe/Istanbul",
    "ankara": "Europe/Istanbul", "izmir": "Europe/Istanbul",
    "uae": "Asia/Dubai", "united arab emirates": "Asia/Dubai", "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai", "sharjah": "Asia/Dubai",
    "saudi arabia": "Asia/Riyadh", "jeddah": "Asia/Riyadh", "mecca": "Asia/Riyadh",
    "medina": "Asia/Riyadh", "qatar": "Asia/Qatar", "kuwait": "Asia/Kuwait",
    "oman": "Asia/Muscat", "bahrain": "Asia/Bahrain", "iran": "Asia/Tehran",
    "iraq": "Asia/Baghdad", "jordan": "Asia/Amman", "lebanon": "Asia/Beirut",
    "egypt": "Africa/Cairo", "israel": "Asia/Jerusalem",
    # Asia
    "bangladesh": "Asia/Dhaka", "nepal": "Asia/Kathmandu", "sri lanka": "Asia/Colombo",
    "china": "Asia/Shanghai", "beijing": "Asia/Shanghai", "shenzhen": "Asia/Shanghai",
    "guangzhou": "Asia/Shanghai", "japan": "Asia/Tokyo", "south korea": "Asia/Seoul",
    "korea": "Asia/Seoul", "singapore": "Asia/Singapore", "malaysia": "Asia/Kuala_Lumpur",
    "thailand": "Asia/Bangkok", "vietnam": "Asia/Ho_Chi_Minh", "hanoi": "Asia/Ho_Chi_Minh",
    "philippines": "Asia/Manila", "hong kong": "Asia/Hong_Kong", "taiwan": "Asia/Taipei",
    # Europe
    "uk": "Europe/London", "united kingdom": "Europe/London", "england": "Europe/London",
    "britain": "Europe/London", "manchester": "Europe/London", "birmingham": "Europe/London",
    "scotland": "Europe/London", "ireland": "Europe/Dublin", "france": "Europe/Paris",
    "germany": "Europe/Berlin", "munich": "Europe/Berlin", "frankfurt": "Europe/Berlin",
    "hamburg": "Europe/Berlin", "italy": "Europe/Rome", "milan": "Europe/Rome",
    "spain": "Europe/Madrid", "barcelona": "Europe/Madrid", "portugal": "Europe/Lisbon",
    "netherlands": "Europe/Amsterdam", "belgium": "Europe/Brussels", "switzerland": "Europe/Zurich",
    "austria": "Europe/Vienna", "sweden": "Europe/Stockholm", "norway": "Europe/Oslo",
    "denmark": "Europe/Copenhagen", "finland": "Europe/Helsinki", "poland": "Europe/Warsaw",
    "greece": "Europe/Athens", "ukraine": "Europe/Kyiv", "kiev": "Europe/Kyiv", "kyiv": "Europe/Kyiv",
    # Americas
    "new york city": "America/New_York", "nyc": "America/New_York", "boston": "America/New_York",
    "washington": "America/New_York", "washington dc": "America/New_York", "miami": "America/New_York",
    "atlanta": "America/New_York", "philadelphia": "America/New_York",
    "houston": "America/Chicago", "dallas": "America/Chicago", "austin": "America/Chicago",
    "san francisco": "America/Los_Angeles", "seattle": "America/Los_Angeles",
    "san diego": "America/Los_Angeles", "san jose": "America/Los_Angeles",
    "las vegas": "America/Los_Angeles", "portland": "America/Los_Angeles",
    "mexico": "America/Mexico_City", "argentina": "America/Argentina/Buenos_Aires",
    # Africa and Oceania
    "nigeria": "Africa/Lagos", "kenya": "Africa/Nairobi", "south africa": "Africa/Johannesburg",
    "cape town": "Africa/Johannesburg", "morocco": "Africa/Casablanca", "ghana": "Africa/Accra",
    "new zealand": "Pacific/Auckland",
}

_ABBREVIATIONS = {
    "pkt": "Asia/Karachi", "gmt": "UTC", "utc": "UTC", "z": "UTC", "bst": "Europe/London",
    "cet": "Europe/Paris", "cest": "Europe/Paris", "est": "America/New_York",
    "edt": "America/New_York", "pst": "America/Los_Angeles", "pdt": "America/Los_Angeles",
    "mst": "America/Denver", "mdt": "America/Denver", "jst": "Asia/Tokyo",
    "sgt": "Asia/Singapore", "aest": "Australia/Sydney", "trt": "Europe/Istanbul",
}

# Offsets in minutes that are not whole hours.
_ODD_OFFSETS = {
    330: "Asia/Kolkata", 345: "Asia/Kathmandu", 210: "Asia/Tehran", 270: "Asia/Kabul",
    390: "Asia/Yangon", 570: "Australia/Darwin", -210: "America/St_Johns",
}

_OFFSET_RE = re.compile(r"^(?:gmt|utc)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$")


def _zone_from_offset(text: str) -> str | None:
    m = _OFFSET_RE.match(text)
    if not m:
        return None
    sign = 1 if m.group(1) == "+" else -1
    hours, minutes = int(m.group(2)), int(m.group(3) or 0)
    total = sign * (hours * 60 + minutes)
    if total in _ODD_OFFSETS:
        return _ODD_OFFSETS[total]
    if minutes != 0 or not -12 <= sign * hours <= 14:
        return None
    if total == 0:
        return "UTC"
    # Etc/GMT zones use an inverted sign: UTC+5 is Etc/GMT-5
    name = f"Etc/GMT{'-' if total > 0 else '+'}{hours}"
    try:
        ZoneInfo(name)
    except Exception:
        return None
    return name


def resolve_timezone(text: str) -> str | None:
    """Turn a city, country, IANA name, abbreviation or GMT offset into an IANA zone."""
    raw = re.sub(r"[^a-z0-9+:/_\-, ]", " ", (text or "").lower())
    raw = " ".join(raw.split())
    if not raw:
        return None

    candidates = [raw] + [p.strip() for p in raw.split(",") if p.strip()]
    for cand in candidates:
        cand = re.sub(r"\s+(time ?zone|time)$", "", cand).strip()
        if cand in _ALIASES:
            return _ALIASES[cand]
        if cand in _ABBREVIATIONS:
            return _ABBREVIATIONS[cand]
        if cand in _ZONE_BY_LOWER:
            return _ZONE_BY_LOWER[cand]
        if cand in _ZONE_BY_CITY:
            return _ZONE_BY_CITY[cand]
        offset_zone = _zone_from_offset(cand)
        if offset_zone:
            return offset_zone
    return None


def _require_timezone(text: str) -> str:
    zone = resolve_timezone(text)
    if not zone:
        raise HTTPException(
            400,
            f"UNKNOWN_TIMEZONE: I couldn't work out the timezone for '{text}'. "
            "Ask the visitor which city they are in (for example Istanbul or Karachi).",
        )
    return zone


def _tz_label(tz_name: str) -> str:
    if tz_name == "UTC" or tz_name.startswith("Etc/"):
        return ""
    return tz_name.split("/")[-1].replace("_", " ")


def _utc_offset(dt: datetime) -> str:
    minutes = int(dt.utcoffset().total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return f"UTC{sign}{minutes // 60:02d}:{minutes % 60:02d}"


def _fmt_when(dt: datetime, tz_name: str = OWNER_TZ_NAME) -> str:
    local = dt.astimezone(ZoneInfo(tz_name))
    label = _tz_label(tz_name)
    place = f" {label} time" if label else ""
    return f"{local:%d %b %Y, %I:%M %p}{place} ({_utc_offset(local)})"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _clean_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please provide a valid email address.")
    return email


def _clean_text(value: str) -> str:
    return " ".join(value.split())


_rate_hits: dict = defaultdict(deque)
_rate_lock = threading.Lock()


def _client_ip(request: FastAPIRequest) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: FastAPIRequest, bucket: str, limit: int, window: int):
    now = time.monotonic()
    key = (bucket, _client_ip(request))
    with _rate_lock:
        hits = _rate_hits[key]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Too many requests. Please slow down.")
        hits.append(now)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: str = Field(..., min_length=1, max_length=100)


class ChatResponse(BaseModel):
    response: str
    thread_id: str


class MeetingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)


class MeetingResponse(BaseModel):
    message: str


class CalendarBookingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=200)
    # Without an offset (2026-10-25T17:00:00) it is read as the visitor's local time.
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: int = Field(default=30, ge=1, le=1440)
    # City, country, IANA name or GMT offset, e.g. "Istanbul", "Karachi", "GMT+5".
    timezone: str = Field(..., min_length=1, max_length=100)
    message: str = Field(default="", max_length=2000)


class CalendarCancelRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)


# ---------------------------------------------------------------------------
# Email (Resend)
# ---------------------------------------------------------------------------
def send_email(subject: str, body: str, reply_to: str | None = None):
    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("MEETING_RECIPIENT_EMAIL")
    if not api_key or not recipient:
        raise HTTPException(500, "Email service is not configured properly.")

    payload = {
        "from": "Portfolio <onboarding@resend.dev>",
        "to": [recipient],
        "subject": _clean_text(subject)[:200],
        "text": body,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=20,
    )
    if r.status_code >= 300:
        raise Exception(f"Resend error {r.status_code}: {r.text}")


# ---------------------------------------------------------------------------
# Basic routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Ayan AI Portfolio API is running.",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: FastAPIRequest):
    rate_limit(http_request, "chat", CHAT_LIMIT, CHAT_WINDOW_SECONDS)
    try:
        config = {"configurable": {"thread_id": request.thread_id}}

        result = ayan_agent.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )

        content = result["messages"][-1].content

        if isinstance(content, list):
            response_text = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
        else:
            response_text = str(content).strip()

        if not response_text:
            response_text = "Sorry, I didn't catch that. Could you rephrase?"

        return ChatResponse(response=response_text, thread_id=request.thread_id)

    except Exception as e:
        print(f"Agent Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="The AI assistant is temporarily unavailable.",
        ) from e


@app.post("/meeting", response_model=MeetingResponse)
def meeting(request: MeetingRequest):
    name = _clean_text(request.name)
    email = _clean_email(request.email)
    message = request.message.strip()
    if not name or not message:
        raise HTTPException(400, "Name and message cannot be empty.")

    try:
        send_email(
            subject=f"New Portfolio Message from {name}",
            body=(
                "New message from your portfolio:\n\n"
                f"Name: {name}\nEmail: {email}\n"
                f"Message: {message}\n"
            ),
            reply_to=email,
        )
        return MeetingResponse(message="Meeting request sent successfully.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Email Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to send meeting request.") from e


# ---------------------------------------------------------------------------
# Google Calendar: credentials
# ---------------------------------------------------------------------------
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]

TOKEN_PATH = Path(
    os.getenv("GOOGLE_TOKEN_JSON", str(Path(__file__).parent / "google_token.json"))
)
print("Google token path:", TOKEN_PATH.resolve(), "exists:", TOKEN_PATH.exists())

_creds_lock = threading.Lock()
_creds_cache = None


def create_google_flow(state=None):
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return flow


def _load_credentials() -> Credentials:
    token_json = os.getenv("GOOGLE_TOKEN_JSON_CONTENT")
    try:
        if token_json:
            return Credentials.from_authorized_user_info(
                json.loads(token_json), GOOGLE_SCOPES
            )
        if TOKEN_PATH.exists():
            return Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
    except (ValueError, KeyError) as e:
        print(f"Token load error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Stored Google token is invalid.") from e

    raise HTTPException(
        status_code=401,
        detail="Google Calendar has not been connected yet.",
    )


def get_calendar_service():
    global _creds_cache
    with _creds_lock:
        if _creds_cache is None:
            _creds_cache = _load_credentials()
        creds = _creds_cache

        if not creds.valid:
            if not creds.refresh_token:
                _creds_cache = None
                raise HTTPException(
                    status_code=401,
                    detail="Google authorization expired. Reconnect Calendar.",
                )
            try:
                creds.refresh(GoogleRequest())
            except RefreshError as e:
                _creds_cache = None
                print(f"Token refresh failed: {e}")
                raise HTTPException(
                    status_code=401,
                    detail="Google authorization expired. Reconnect Calendar.",
                ) from e

            if not os.getenv("GOOGLE_TOKEN_JSON_CONTENT"):
                try:
                    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
                except OSError as e:
                    print(f"Could not save refreshed token: {e}")

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Google Calendar: OAuth (local use only)
# ---------------------------------------------------------------------------
def _oauth_allowed():
    # When the token comes from an env variable (production), these routes are
    # switched off so nobody can replace your calendar connection.
    if os.getenv("GOOGLE_TOKEN_JSON_CONTENT"):
        raise HTTPException(404, "Not found.")


@app.get("/oauth/start")
def oauth_start():
    _oauth_allowed()
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(500, "Google OAuth is not configured.")

    flow = create_google_flow()
    url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return RedirectResponse(url)


@app.get("/oauth/callback")
def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    global _creds_cache
    _oauth_allowed()
    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

        with _creds_lock:
            _creds_cache = None

        print("Token saved to:", TOKEN_PATH.resolve())
        return {
            "status": "connected",
            "message": "Google Calendar authorization saved successfully!",
            "saved_to": str(TOKEN_PATH.resolve()),
        }
    except Exception as e:
        print(f"Google OAuth Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Google authorization failed: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# Google Calendar: helpers
# ---------------------------------------------------------------------------
def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _event_range(e: dict):
    s, en = e["start"], e["end"]
    if "dateTime" in s:
        return _parse_dt(s["dateTime"]), _parse_dt(en["dateTime"])
    # all-day event (end date is exclusive in Google Calendar)
    return (
        datetime.fromisoformat(s["date"]).replace(tzinfo=OWNER_TZ),
        datetime.fromisoformat(en["date"]).replace(tzinfo=OWNER_TZ),
    )


def _event_tz(e: dict) -> str:
    name = (e.get("start") or {}).get("timeZone")
    try:
        ZoneInfo(name)
        return name
    except Exception:
        return OWNER_TZ_NAME


def _is_portfolio_event(e: dict) -> bool:
    private = (e.get("extendedProperties") or {}).get("private") or {}
    return private.get("source") == "portfolio-ai" or e.get(
        "summary", ""
    ).startswith("Portfolio meeting with")


def _blocks_time(e: dict) -> bool:
    return e.get("status") != "cancelled" and e.get("transparency") != "transparent"


def _upcoming_visitor_events(service, email: str) -> list:
    """Upcoming portfolio meetings where this email is an attendee."""
    items = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=datetime.now(UTC).isoformat(),
            singleEvents=True,
            orderBy="startTime",
            q=email,
            maxResults=50,
        )
        .execute()
        .get("items", [])
    )

    found = []
    for e in items:
        if e.get("status") == "cancelled" or not _is_portfolio_event(e):
            continue
        attendees = [a.get("email", "").lower() for a in e.get("attendees", [])]
        if email in attendees:
            found.append(e)
    return found


# ---------------------------------------------------------------------------
# Google Calendar: endpoints
# ---------------------------------------------------------------------------
@app.get("/timezone/resolve")
def timezone_resolve(place: str = Query(..., min_length=1, max_length=100)):
    zone = _require_timezone(place)
    now = datetime.now(ZoneInfo(zone))
    return {"timezone": zone, "utc_offset": _utc_offset(now)}


@app.get("/calendar/availability")
def calendar_availability(
    day: str = Query(..., description="YYYY-MM-DD, the visitor's local date"),
    duration: int = Query(30),
    timezone: str = Query(OWNER_TZ_NAME, description="Visitor's city or timezone"),
):
    if not MIN_DURATION <= duration <= MAX_DURATION:
        raise HTTPException(
            400, f"Duration must be between {MIN_DURATION} and {MAX_DURATION} minutes."
        )
    try:
        d = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Date must be in YYYY-MM-DD format.")

    tz_name = _require_timezone(timezone)
    tz = ZoneInfo(tz_name)

    day_start = datetime(d.year, d.month, d.day, tzinfo=tz)
    nxt = d + timedelta(days=1)
    day_end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz)
    now = datetime.now(tz)

    base = {
        "date": day,
        "timezone": f"{_tz_label(tz_name) or tz_name} ({_utc_offset(day_start)})",
        "duration": duration,
        "ayan_hours": f"{DAY_START_HOUR:02d}:00 to {DAY_END_HOUR:02d}:00 Karachi time",
    }

    if d.date() < now.date():
        return {**base, "free_slots": [], "note": "That date is in the past."}
    if d.date() > (now + timedelta(days=MAX_DAYS_AHEAD)).date():
        return {
            **base,
            "free_slots": [],
            "note": f"Meetings can only be booked up to {MAX_DAYS_AHEAD} days ahead.",
        }

    try:
        service = get_calendar_service()
        items = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                maxResults=250,
            )
            .execute()
            .get("items", [])
        )
        busy = [_event_range(e) for e in items if _blocks_time(e)]

        step = timedelta(minutes=SLOT_STEP_MINUTES)
        length = timedelta(minutes=duration)
        now_utc = datetime.now(UTC)

        slots = []
        cur = day_start.astimezone(UTC)
        stop = day_end.astimezone(UTC)
        while cur + length <= stop:
            end = cur + length
            oc, oe = cur.astimezone(OWNER_TZ), end.astimezone(OWNER_TZ)
            in_hours = (
                oc.date() == oe.date()
                and oc.hour * 60 + oc.minute >= DAY_START_HOUR * 60
                and oe.hour * 60 + oe.minute <= DAY_END_HOUR * 60
            )
            is_free = not any(cur < b_end and end > b_start for b_start, b_end in busy)
            if in_hours and is_free and cur > now_utc:
                local = cur.astimezone(tz)
                slots.append(
                    {
                        "start": local.isoformat(),
                        "label": local.strftime("%I:%M %p"),
                        "ayan_time": oc.strftime("%I:%M %p"),
                    }
                )
            cur += step

        return {**base, "free_slots": slots}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Availability Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to check availability.") from e


@app.post("/calendar/book")
def book_calendar_event(request: CalendarBookingRequest):
    name = _clean_text(request.name)
    email = _clean_email(request.email)
    if not name:
        raise HTTPException(400, "Name cannot be empty.")

    tz_name = _require_timezone(request.timezone)
    tz = ZoneInfo(tz_name)

    # A time without an offset is the visitor's local time.
    start = request.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=tz)

    if request.end_time is not None:
        end = request.end_time
        if end.tzinfo is None:
            end = end.replace(tzinfo=tz)
    else:
        end = start.astimezone(UTC) + timedelta(minutes=request.duration_minutes)

    start, end = start.astimezone(tz), end.astimezone(tz)

    if end <= start:
        raise HTTPException(400, "End time must be after start time.")

    minutes = (end - start).total_seconds() / 60
    if not MIN_DURATION <= minutes <= MAX_DURATION:
        raise HTTPException(
            400, f"Meeting length must be between {MIN_DURATION} and {MAX_DURATION} minutes."
        )

    now_utc = datetime.now(UTC)
    if start <= now_utc:
        raise HTTPException(400, "That time is in the past. Please choose a future time.")
    if start > now_utc + timedelta(days=MAX_DAYS_AHEAD):
        raise HTTPException(
            400, f"Meetings can only be booked up to {MAX_DAYS_AHEAD} days ahead."
        )

    try:
        with BOOKING_LOCK:
            service = get_calendar_service()

            mine = _upcoming_visitor_events(service, email)
            if mine:
                when = _fmt_when(_event_range(mine[0])[0], _event_tz(mine[0]))
                raise HTTPException(
                    status_code=409,
                    detail=f"ALREADY_BOOKED: {email} already has an upcoming meeting on {when}.",
                )

            existing = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    maxResults=50,
                )
                .execute()
                .get("items", [])
            )
            if any(_blocks_time(e) for e in existing):
                raise HTTPException(
                    status_code=409,
                    detail="SLOT_TAKEN: That time slot is already booked. Please choose a different time.",
                )

            event = {
                "summary": f"Portfolio meeting with {name}",
                "description": request.message.strip() or "Meeting requested via Ayan's portfolio.",
                "start": {"dateTime": start.isoformat(), "timeZone": tz_name},
                "end": {"dateTime": end.isoformat(), "timeZone": tz_name},
                "attendees": [{"email": email}],
                "extendedProperties": {"private": {"source": "portfolio-ai"}},
                "conferenceData": {
                    "createRequest": {
                        "requestId": uuid.uuid4().hex,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }

            created = (
                service.events()
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1,
                    sendUpdates="all",
                )
                .execute()
            )

        visitor_time = f"{_fmt_when(start, tz_name)} for {int(minutes)} min"
        ayan_time = _fmt_when(start, OWNER_TZ_NAME)
        try:
            send_email(
                subject=f"Meeting booked: {name}",
                body=(
                    f"{name} ({email}) booked a meeting.\n"
                    f"Visitor's time: {visitor_time}\n"
                    f"Your time: {ayan_time}\n"
                    f"Notes: {request.message.strip() or '-'}\n"
                    f"Calendar: {created.get('htmlLink')}\n"
                ),
                reply_to=email,
            )
        except Exception as e:
            print(f"Notification email failed: {e}")

        meet_link = created.get("hangoutLink") or next(
            (
                item.get("uri")
                for item in created.get("conferenceData", {}).get("entryPoints", [])
                if item.get("entryPointType") == "video"
            ),
            None,
        )

        return {
            "status": "created",
            "when": visitor_time,
            "ayan_time": ayan_time,
            "event_link": created.get("htmlLink"),
            "meet_link": meet_link,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Calendar Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to create calendar meeting.",
        ) from e


@app.post("/calendar/cancel")
def cancel_calendar_event(request: CalendarCancelRequest):
    email = _clean_email(request.email)
    try:
        with BOOKING_LOCK:
            service = get_calendar_service()
            events = _upcoming_visitor_events(service, email)
            if not events:
                raise HTTPException(404, "No upcoming meeting found for this email.")

            cancelled = []
            for e in events:
                service.events().delete(
                    calendarId="primary", eventId=e["id"], sendUpdates="all"
                ).execute()
                cancelled.append(_fmt_when(_event_range(e)[0], _event_tz(e)))

        try:
            send_email(
                subject=f"Meeting cancelled: {email}",
                body=f"{email} cancelled their meeting(s): {', '.join(cancelled)}",
            )
        except Exception as e:
            print(f"Cancel notification failed: {e}")

        return {"status": "cancelled", "cancelled": cancelled}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Cancel Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to cancel the meeting.") from e


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)