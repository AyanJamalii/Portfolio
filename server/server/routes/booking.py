"""Calendar endpoints: timezone lookup, availability, booking and cancelling."""

import threading
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from ..calendar_helpers import (
    blocks_time,
    event_range,
    event_tz,
    upcoming_visitor_events,
)
from ..config import (
    DAY_END_HOUR,
    DAY_START_HOUR,
    MAX_DAYS_AHEAD,
    MAX_DURATION,
    MIN_DURATION,
    OWNER_TZ,
    OWNER_TZ_NAME,
    SLOT_STEP_MINUTES,
    UTC,
)
from ..email_service import send_email
from ..google_auth import get_calendar_service
from ..schemas import CalendarBookingRequest, CalendarCancelRequest
from ..timezones import fmt_when, require_timezone, tz_label, utc_offset
from ..utils import clean_email, clean_text

router = APIRouter()

# Stops two simultaneous requests from taking the same slot.
BOOKING_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Timezone lookup
# ---------------------------------------------------------------------------
@router.get("/timezone/resolve")
def timezone_resolve(place: str = Query(..., min_length=1, max_length=100)):
    zone = require_timezone(place)
    return {"timezone": zone, "utc_offset": utc_offset(datetime.now(ZoneInfo(zone)))}


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
def _free_slots(day_start: datetime, day_end: datetime, tz, duration: int, busy: list) -> list:
    """Free slots inside Ayan's working hours, shown in the visitor's timezone."""
    step = timedelta(minutes=SLOT_STEP_MINUTES)
    length = timedelta(minutes=duration)
    now_utc = datetime.now(UTC)

    slots = []
    cur = day_start.astimezone(UTC)
    stop = day_end.astimezone(UTC)
    while cur + length <= stop:
        end = cur + length
        ayan_start, ayan_end = cur.astimezone(OWNER_TZ), end.astimezone(OWNER_TZ)

        in_hours = (
            ayan_start.date() == ayan_end.date()
            and ayan_start.hour * 60 + ayan_start.minute >= DAY_START_HOUR * 60
            and ayan_end.hour * 60 + ayan_end.minute <= DAY_END_HOUR * 60
        )
        is_free = not any(cur < b_end and end > b_start for b_start, b_end in busy)

        if in_hours and is_free and cur > now_utc:
            local = cur.astimezone(tz)
            slots.append(
                {
                    "start": local.isoformat(),
                    "label": local.strftime("%I:%M %p"),
                    "ayan_time": ayan_start.strftime("%I:%M %p"),
                }
            )
        cur += step
    return slots


@router.get("/calendar/availability")
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
    except ValueError as e:
        raise HTTPException(400, "Date must be in YYYY-MM-DD format.") from e

    tz_name = require_timezone(timezone)
    tz = ZoneInfo(tz_name)

    day_start = datetime(d.year, d.month, d.day, tzinfo=tz)
    nxt = d + timedelta(days=1)
    day_end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz)
    now = datetime.now(tz)

    base = {
        "date": day,
        "timezone": f"{tz_label(tz_name) or tz_name} ({utc_offset(day_start)})",
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
        busy = [event_range(e) for e in items if blocks_time(e)]
        return {**base, "free_slots": _free_slots(day_start, day_end, tz, duration, busy)}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Availability Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to check availability.") from e


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------
def _booking_window(request: CalendarBookingRequest, tz) -> tuple[datetime, datetime, int]:
    """Work out (start, end, minutes) in the visitor's timezone and validate them."""
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

    minutes = int((end - start).total_seconds() / 60)
    if not MIN_DURATION <= minutes <= MAX_DURATION:
        raise HTTPException(
            400,
            f"Meeting length must be between {MIN_DURATION} and {MAX_DURATION} minutes.",
        )

    now_utc = datetime.now(UTC)
    if start <= now_utc:
        raise HTTPException(400, "That time is in the past. Please choose a future time.")
    if start > now_utc + timedelta(days=MAX_DAYS_AHEAD):
        raise HTTPException(400, f"Meetings can only be booked up to {MAX_DAYS_AHEAD} days ahead.")

    return start, end, minutes


def _event_body(name: str, email: str, message: str, start, end, tz_name: str) -> dict:
    return {
        "summary": f"Portfolio meeting with {name}",
        "description": message.strip() or "Meeting requested via Ayan's portfolio.",
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


def _meet_link(created: dict) -> str | None:
    return created.get("hangoutLink") or next(
        (
            item.get("uri")
            for item in created.get("conferenceData", {}).get("entryPoints", [])
            if item.get("entryPointType") == "video"
        ),
        None,
    )


def _ensure_slot_is_free(service, email: str, start: datetime, end: datetime):
    """Raise 409 if this visitor already has a meeting, or the slot is taken."""
    mine = upcoming_visitor_events(service, email)
    if mine:
        when = fmt_when(event_range(mine[0])[0], event_tz(mine[0]))
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
    if any(blocks_time(e) for e in existing):
        raise HTTPException(
            status_code=409,
            detail=(
                "SLOT_TAKEN: That time slot is already booked. Please choose a different time."
            ),
        )


@router.post("/calendar/book")
def book_calendar_event(request: CalendarBookingRequest):
    name = clean_text(request.name)
    email = clean_email(request.email)
    if not name:
        raise HTTPException(400, "Name cannot be empty.")

    tz_name = require_timezone(request.timezone)
    start, end, minutes = _booking_window(request, ZoneInfo(tz_name))

    try:
        with BOOKING_LOCK:
            service = get_calendar_service()
            _ensure_slot_is_free(service, email, start, end)
            created = (
                service.events()
                .insert(
                    calendarId="primary",
                    body=_event_body(name, email, request.message, start, end, tz_name),
                    conferenceDataVersion=1,
                    sendUpdates="all",
                )
                .execute()
            )

        visitor_time = f"{fmt_when(start, tz_name)} for {minutes} min"
        ayan_time = fmt_when(start, OWNER_TZ_NAME)
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

        return {
            "status": "created",
            "when": visitor_time,
            "ayan_time": ayan_time,
            "event_link": created.get("htmlLink"),
            "meet_link": _meet_link(created),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Calendar Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to create calendar meeting.") from e


# ---------------------------------------------------------------------------
# Cancelling
# ---------------------------------------------------------------------------
@router.post("/calendar/cancel")
def cancel_calendar_event(request: CalendarCancelRequest):
    email = clean_email(request.email)
    try:
        with BOOKING_LOCK:
            service = get_calendar_service()
            events = upcoming_visitor_events(service, email)
            if not events:
                raise HTTPException(404, "No upcoming meeting found for this email.")

            cancelled = []
            for e in events:
                service.events().delete(
                    calendarId="primary", eventId=e["id"], sendUpdates="all"
                ).execute()
                cancelled.append(fmt_when(event_range(e)[0], event_tz(e)))

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
