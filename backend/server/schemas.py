"""Request and response models."""

from datetime import datetime

from pydantic import BaseModel, Field


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
