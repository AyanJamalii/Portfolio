import os
import smtplib
from email.message import EmailMessage
import requests

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

def send_email(subject: str, body: str, reply_to: str | None = None):
    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("MEETING_RECIPIENT_EMAIL")
    if not api_key or not recipient:
        raise HTTPException(500, "Email service is not configured properly.")

    payload = {
        "from": "Portfolio <onboarding@resend.dev>",
        "to": [recipient],
        "subject": subject,
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
        send_email(
            subject=f"New Portfolio Meeting Request from {request.name}",
            body=(
                "New meeting request from your portfolio:\n\n"
                f"Name: {request.name}\nEmail: {request.email}\n"
                f"Message: {request.message}\n"
            ),
            reply_to=request.email,
        )
        return MeetingResponse(message="Meeting request sent successfully.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Email Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to send meeting request.") from e


# Google Calendar integration
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]

TOKEN_PATH = Path(
    os.getenv("GOOGLE_TOKEN_JSON", str(Path(__file__).parent / "google_token.json"))
)
print("Google token path:", TOKEN_PATH.resolve(), "exists:", TOKEN_PATH.exists())


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


def get_calendar_service():
    print("CWD:", Path.cwd())
    print("Token path:", TOKEN_PATH.resolve(), "exists:", TOKEN_PATH.exists())

    if not TOKEN_PATH.exists():
        raise HTTPException(
            status_code=401,
            detail="Google Calendar has not been connected yet.",
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_PATH), GOOGLE_SCOPES
    )
    print("Has refresh token:", bool(credentials.refresh_token), "expired:", credentials.expired)



@app.get("/oauth/start")
def oauth_start():
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
    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

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

        try:
            send_email(
                subject=f"Meeting booked: {request.name}",
                body=(
                    f"{request.name} ({request.email}) booked a meeting.\n"
                    f"Start: {start.isoformat()}\nEnd: {end.isoformat()}\n"
                    f"Notes: {request.message}\nCalendar: {created.get('htmlLink')}\n"
                ),
                reply_to=request.email,
            )
        except Exception as e:
            print(f"Notification email failed: {e}")

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