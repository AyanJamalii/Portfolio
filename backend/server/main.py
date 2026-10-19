import os
import smtplib
from email.message import EmailMessage

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from agents.graph import ayan_agent
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

app = FastAPI(
    title="Ayan AI Portfolio API",
    description="Backend API for Ayan's AI portfolio assistant.",
    version="1.0.0",
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


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    thread_id: str


class MeetingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)


class MeetingResponse(BaseModel):
    message: str


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
def chat(request: ChatRequest):
    try:
        config = {
            "configurable": {
                "thread_id": request.thread_id,
            }
        }

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
            response_text = str(content)

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id,
        )

    except Exception as e:
        print(f"Agent Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="The AI assistant is temporarily unavailable.",
        ) from e


@app.post("/meeting", response_model=MeetingResponse)
def meeting(request: MeetingRequest):
    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        recipient_email = os.getenv("MEETING_RECIPIENT_EMAIL")

        if not all([
            smtp_host,
            smtp_username,
            smtp_password,
            recipient_email,
        ]):
            raise HTTPException(
                status_code=500,
                detail="Email service is not configured properly.",
            )

        email_message = EmailMessage()
        email_message["Subject"] = (
            f"New Portfolio Meeting Request from {request.name}"
        )
        email_message["From"] = smtp_username
        email_message["To"] = recipient_email
        email_message["Reply-To"] = request.email

        email_message.set_content(
            "New meeting request from your portfolio:\n\n"
            f"Name: {request.name}\n"
            f"Email: {request.email}\n"
            f"Message: {request.message}\n\n"
            "You can reply directly to this email."
        )

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(email_message)

        return MeetingResponse(
            message="Meeting request sent successfully."
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Email Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to send meeting request.",
        ) from e


# Google Calendar integration
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]

TOKEN_PATH = Path(os.getenv("GOOGLE_TOKEN_JSON", "google_token.json"))


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
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return flow


def get_calendar_service():
    if not TOKEN_PATH.exists():
        raise HTTPException(
            status_code=401,
            detail="Google Calendar has not been connected yet.",
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_PATH), GOOGLE_SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

    if not credentials.valid:
        raise HTTPException(
            status_code=401,
            detail="Google authorization expired. Reconnect Calendar.",
        )

    return build("calendar", "v3", credentials=credentials)


@app.get("/oauth/start")
def oauth_start():
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv(
        "GOOGLE_CLIENT_SECRET"
    ):
        raise HTTPException(500, "Google OAuth is not configured.")

    flow = create_google_flow()
    url, _ = flow.authorization_url(
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
    flow = create_google_flow(state=state)
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

        return {
            "status": "connected",
            "message": "Google Calendar authorization saved.",
        }
    except Exception as e:
        print(f"Google OAuth Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Google authorization failed.",
        ) from e


class CalendarBookingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=200)
    start_time: datetime
    end_time: datetime
    timezone: str = Field(..., min_length=1, max_length=100)
    message: str = Field(default="", max_length=2000)


@app.post("/calendar/book")
def book_calendar_event(request: CalendarBookingRequest):
    try:
        tz = ZoneInfo(request.timezone)

        start = request.start_time
        end = request.end_time

        if start.tzinfo is None or end.tzinfo is None:
            raise HTTPException(
                400, "Include timezone offsets in start_time and end_time."
            )

        if end <= start:
            raise HTTPException(400, "End time must be after start time.")

        service = get_calendar_service()

        event = {
            "summary": f"Portfolio meeting with {request.name}",
            "description": request.message or "Meeting requested via Ayan's portfolio.",
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": request.timezone,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": request.timezone,
            },
            "attendees": [{"email": request.email}],
            "conferenceData": {
                "createRequest": {
                    "requestId": __import__("uuid").uuid4().hex,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        created = service.events().insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all",
        ).execute()

        meet_link = created.get("hangoutLink")
        if not meet_link:
            meet_link = next(
                (
                    item.get("uri")
                    for item in created.get(
                        "conferenceData", {}
                    ).get("entryPoints", [])
                    if item.get("entryPointType") == "video"
                ),
                None,
            )

        return {
            "status": "created",
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)