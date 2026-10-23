"""Turn what a visitor says ("Istanbul", "GMT+5") into a real timezone, and format times."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

from fastapi import HTTPException

from .config import OWNER_TZ_NAME
from .tz_data import ABBREVIATIONS, ALIASES, ODD_OFFSETS

_CONTINENTS = (
    "Africa/",
    "America/",
    "Antarctica/",
    "Arctic/",
    "Asia/",
    "Atlantic/",
    "Australia/",
    "Europe/",
    "Indian/",
    "Pacific/",
)
_OFFSET_RE = re.compile(r"^(?:gmt|utc)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$")

# "asia/karachi" -> "Asia/Karachi" and "karachi" -> "Asia/Karachi"
_ZONE_BY_LOWER: dict[str, str] = {}
_ZONE_BY_CITY: dict[str, str] = {}
for _zone in sorted(available_timezones()):
    if not _zone.startswith(_CONTINENTS):
        continue
    _ZONE_BY_LOWER[_zone.lower()] = _zone
    _ZONE_BY_CITY.setdefault(_zone.split("/")[-1].replace("_", " ").lower(), _zone)


def _zone_from_offset(text: str) -> str | None:
    m = _OFFSET_RE.match(text)
    if not m:
        return None
    sign = 1 if m.group(1) == "+" else -1
    hours, minutes = int(m.group(2)), int(m.group(3) or 0)
    total = sign * (hours * 60 + minutes)
    if total in ODD_OFFSETS:
        return ODD_OFFSETS[total]
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
        for table in (ALIASES, ABBREVIATIONS, _ZONE_BY_LOWER, _ZONE_BY_CITY):
            if cand in table:
                return table[cand]
        offset_zone = _zone_from_offset(cand)
        if offset_zone:
            return offset_zone
    return None


def require_timezone(text: str) -> str:
    zone = resolve_timezone(text)
    if not zone:
        raise HTTPException(
            400,
            f"UNKNOWN_TIMEZONE: I couldn't work out the timezone for '{text}'. "
            "Ask the visitor which city they are in (for example Istanbul or Karachi).",
        )
    return zone


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def tz_label(tz_name: str) -> str:
    """'Europe/Istanbul' -> 'Istanbul'. Fixed-offset zones have no label."""
    if tz_name == "UTC" or tz_name.startswith("Etc/"):
        return ""
    return tz_name.split("/")[-1].replace("_", " ")


def utc_offset(dt: datetime) -> str:
    minutes = int(dt.utcoffset().total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return f"UTC{sign}{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_when(dt: datetime, tz_name: str = OWNER_TZ_NAME) -> str:
    """'25 Oct 2026, 05:00 PM Istanbul time (UTC+03:00)'"""
    local = dt.astimezone(ZoneInfo(tz_name))
    label = tz_label(tz_name)
    place = f" {label} time" if label else ""
    return f"{local:%d %b %Y, %I:%M %p}{place} ({utc_offset(local)})"
