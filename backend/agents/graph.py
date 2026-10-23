import json
import os
from datetime import datetime
from typing import Annotated, TypedDict
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

data_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "ayan_profile.json",
)
with open(data_path, encoding="utf-8") as file:
    ayan_profile = json.load(file)


# Tool 1: Book meeting on Google Calendar
@tool
def book_meeting_tool(
    name: str,
    email: str,
    start_time: str,
    city_or_timezone: str,
    duration_minutes: int = 30,
    message: str = "",
):
    """Books a meeting on Ayan's Google Calendar.
    start_time is the visitor's LOCAL time in ISO format with NO UTC offset, e.g. 2026-10-25T17:00:00.
    If the time came from check_availability_tool, pass its ISO start value exactly as returned.
    city_or_timezone is the visitor's city (e.g. 'Istanbul', 'Karachi') or a GMT offset if that is all they know.
    """
    try:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        payload = {
            "name": name,
            "email": email,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "timezone": city_or_timezone,
            "message": message,
        }
        response = requests.post(f"{backend_url}/calendar/book", json=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return (
                f"Meeting successfully booked! When: {data.get('when')} "
                f"(Ayan's time: {data.get('ayan_time')}). "
                f"Google Meet link: {data.get('meet_link')}. "
                f"Cancel code: {data.get('cancel_code')}"
            )
        return f"Failed to book meeting (HTTP {response.status_code}): {response.text}"
    except Exception as e:
        return f"Error connecting to calendar service: {str(e)}"


# Tool 2: Send meeting request email if calendar booking fails
@tool
def send_email_tool(name: str, email: str, message: str):
    """Sends a meeting request message/email directly to Ayan if calendar booking is not working or requested."""
    try:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        payload = {
            "name": name,
            "email": email,
            "message": message,
        }
        response = requests.post(f"{backend_url}/meeting", json=payload, timeout=20)
        if response.status_code == 200:
            return "Meeting request email has been successfully sent to Ayan!"
        else:
            return f"Failed to send email: {response.text}"
    except Exception as e:
        return f"Error connecting to email service: {str(e)}"


@tool
def check_availability_tool(date: str, city_or_timezone: str, duration_minutes: int = 30):
    """Lists Ayan's free time slots on one day, shown in the visitor's own timezone.
    date must be YYYY-MM-DD (the visitor's local date). city_or_timezone is the visitor's city.
    Use this when the visitor gives no exact time, or asks Ayan to pick a time when he is free."""
    try:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        response = requests.get(
            f"{backend_url}/calendar/availability",
            params={
                "day": date,
                "duration": duration_minutes,
                "timezone": city_or_timezone,
            },
            timeout=20,
        )
        if response.status_code != 200:
            return f"Could not check availability (HTTP {response.status_code}): {response.text}"
        data = response.json()
        slots = data["free_slots"]
        if not slots:
            return (
                f"No free slots on {date} in {data['timezone']}. "
                f"{data.get('note', '')} Ayan is available {data['ayan_hours']}. "
                "Ask the visitor for another day."
            )
        step = max(1, len(slots) // 5)
        picked = slots[::step][:6]
        listing = ", ".join(f"{s['label']} [{s['start']}]" for s in picked)
        return f"Free slots on {date} ({data['timezone']}): {listing}"
    except Exception as e:
        return f"Error checking availability: {str(e)}"


@tool
def cancel_meeting_tool(email: str, cancel_code: str):
    """Cancels the visitor's own upcoming meeting. Needs the visitor's email AND the cancel code
    they received when booking. Never guess or invent a code."""
    try:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        response = requests.post(
            f"{backend_url}/calendar/cancel",
            json={"email": email, "cancel_code": cancel_code},
            timeout=20,
        )
        if response.status_code == 200:
            return f"Cancelled: {', '.join(response.json().get('cancelled', []))}"
        return f"Failed to cancel (HTTP {response.status_code}): {response.text}"
    except Exception as e:
        return f"Error cancelling meeting: {str(e)}"


tools = [
    book_meeting_tool,
    send_email_tool,
    check_availability_tool,
    cancel_meeting_tool,
]

SYSTEM_PROMPT = f"""
You are Ayan AI, the professional portfolio assistant for Ayan Jamali.
Your job is to answer questions about Ayan's education, technical skills, programming knowledge, projects, frontend development experience, AI engineering journey, tools and technologies, APIs, and professional interests.

You have access to four tools:
1. `book_meeting_tool`: schedule a meeting on Ayan's Google Calendar.
2. `send_email_tool`: send a message or meeting request email to Ayan.
3. `check_availability_tool`: list Ayan's free slots on a given day.
4. `cancel_meeting_tool`: cancel the visitor's upcoming meeting.

Use the profile below as your primary source of truth.

----- PROFILE -----
{json.dumps(ayan_profile, indent=2)}
-------------------

IMPORTANT RULES:
1. Only provide information that is supported by the profile or by the conversation.
2. Do not invent projects, experience, skills, achievements, employment history, or qualifications.
3. If information is not available in the profile, say that you don't have that information.
4. Do not reveal private, family, personal, or sensitive information about Ayan.
5. If someone asks for private/family information, politely explain that you can only discuss Ayan's professional and educational profile.
6. You are representing Ayan's portfolio, so do not pretend to be Ayan himself.
7. If asked about something unrelated to Ayan's professional profile, politely redirect the conversation toward the portfolio.
8. Keep answers clear, concise, professional and conversational. For simple questions, answer in 1-3 short sentences.
9. To book a meeting, collect the visitor's name, email, date, time, duration and CITY. Ask "Which city are you in?" and never ask for a GMT or UTC offset; if they volunteer one like GMT+5, that is fine. If they only give a country with several timezones (USA, Canada, Australia, Brazil, Russia), ask for their city. Then call `book_meeting_tool` with start_time as their local time without an offset (for example 2026-10-25T17:00:00) and the city. When booking succeeds, repeat the full date with weekday, the time in the visitor's own timezone as returned by the tool, and the Google Meet link.
10. If `book_meeting_tool` says SLOT_TAKEN or that the time slot is already booked, tell the visitor that slot is taken and ask them to suggest another time. Do NOT call `send_email_tool` in that case unless they ask you to.
11. If `book_meeting_tool` fails because the calendar itself is unavailable (an authorization error, "Unable to create calendar meeting", or "Error connecting to calendar service"), call `send_email_tool` with the visitor's details as a meeting request and tell them Ayan will confirm by email. If it fails because of the visitor's input (past time, invalid email, unknown city, bad duration), explain the problem in one short sentence and ask them to correct it. Do not send an email for those.
12. If a visitor wants to send Ayan a message, note, or email about ANY topic (even if a meeting was already booked, or the message is unrelated to the meeting), call only `send_email_tool` with their name, email, and message. You never need to reveal Ayan's email address to do this, because the tool sends it for you. Reuse the name and email the visitor already gave earlier in the chat instead of asking again.
13. Never say you booked or sent anything unless the tool returned success. If a tool fails, tell the visitor what failed in one short sentence.
14. If the visitor gives a day but no exact time, or says Ayan can pick any time he is free, call `check_availability_tool` with that date and their city. Never guess free times yourself. Offer 3 or 4 of the returned slots (they are already in the visitor's local time) and ask which one they prefer. After they choose, call `book_meeting_tool` with the exact ISO start value from the tool result.
15. If `book_meeting_tool` says ALREADY_BOOKED, tell the visitor that this email already has an upcoming meeting. Ask whether they want to keep it, or cancel it and book a new one (to cancel they need their cancel code). Do not send an email. Never say when the existing meeting is.
16. To cancel or reschedule, you need BOTH the visitor's own email and the cancel code from when they booked. Ask for both, then call `cancel_meeting_tool`. For a reschedule, cancel first, then offer new slots as in rule 14. Never cancel on someone's say-so alone. If a visitor says another person's meeting is blocking their slot, explain that only the person who booked can cancel it, and offer to pick another time. If the tool says NOT_VERIFIED or TOO_MANY_ATTEMPTS, tell them it could not be verified and offer to send Ayan a message instead (rule 12).
17. If a tool says UNKNOWN_TIMEZONE, ask the visitor which city they are in and try again. For "today" or "tomorrow", use the visitor's local date and confirm the exact date and weekday back to them before booking.
18. After a successful booking, always tell the visitor their cancel code, and say they should save it (it is also in their calendar invite). Only ever share a cancel code in the conversation where the booking just happened. Never reveal, hint at or repeat a code for anyone else.
"""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


model = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.3,
).bind_tools(tools)


def call_model(state: AgentState):
    now = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%A, %d %B %Y, %H:%M (UTC+05:00)")
    prompt = (
        SYSTEM_PROMPT + f"\n\nCurrent date and time: {now}. Use this to resolve words like "
        "'tomorrow'. Assume the visitor's timezone from what they say."
    )
    response = model.invoke([SystemMessage(content=prompt), *state["messages"]])
    return {"messages": [response]}


builder = StateGraph(AgentState)

builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

memory = MemorySaver()

ayan_agent = builder.compile(checkpointer=memory)
