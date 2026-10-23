"""Helpers for reading Google Calendar events."""

from datetime import datetime
from zoneinfo import ZoneInfo

from .config import OWNER_TZ, OWNER_TZ_NAME, UTC


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def event_range(e: dict) -> tuple[datetime, datetime]:
    s, en = e["start"], e["end"]
    if "dateTime" in s:
        return parse_dt(s["dateTime"]), parse_dt(en["dateTime"])
    # all-day event (the end date is exclusive in Google Calendar)
    return (
        datetime.fromisoformat(s["date"]).replace(tzinfo=OWNER_TZ),
        datetime.fromisoformat(en["date"]).replace(tzinfo=OWNER_TZ),
    )


def event_tz(e: dict) -> str:
    name = (e.get("start") or {}).get("timeZone")
    try:
        ZoneInfo(name)
        return name
    except Exception:
        return OWNER_TZ_NAME


def is_portfolio_event(e: dict) -> bool:
    private = (e.get("extendedProperties") or {}).get("private") or {}
    return private.get("source") == "portfolio-ai" or e.get("summary", "").startswith(
        "Portfolio meeting with"
    )


def blocks_time(e: dict) -> bool:
    """Cancelled events and events marked 'free' do not block a slot."""
    return e.get("status") != "cancelled" and e.get("transparency") != "transparent"


def upcoming_visitor_events(service, email: str) -> list:
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
        if e.get("status") == "cancelled" or not is_portfolio_event(e):
            continue
        attendees = [a.get("email", "").lower() for a in e.get("attendees", [])]
        if email in attendees:
            found.append(e)
    return found
