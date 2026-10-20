import json
import os
from datetime import datetime
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import requests
from zoneinfo import ZoneInfo

load_dotenv()

data_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "ayan_profile.json",
)
with open(data_path, "r", encoding="utf-8") as file:
    ayan_profile = json.load(file)


# Tool 1: Book meeting on Google Calendar
@tool
def book_meeting_tool(
    name: str, email: str, start_time: str, end_time: str, message: str = ""
):
    """Books a meeting on Ayan's Google Calendar.
    Times must be provided in ISO format with timezone offsets (e.g., 2026-10-25T15:00:00+05:00).
    """
    try:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        payload = {
            "name": name,
            "email": email,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": "Asia/Karachi",
            "message": message,
        }
        response = requests.post(
            f"{backend_url}/calendar/book", json=payload, timeout=20
        )
        if response.status_code == 200:
            data = response.json()
            return f"Meeting successfully booked! Google Meet link: {data.get('meet_link')}"
        else:
            return f"Failed to book meeting: {response.text}"
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
        response = requests.post(
            f"{backend_url}/meeting", json=payload, timeout=20
        )
        if response.status_code == 200:
            return "Meeting request email has been successfully sent to Ayan!"
        else:
            return f"Failed to send email: {response.text}"
    except Exception as e:
        return f"Error connecting to email service: {str(e)}"


tools = [book_meeting_tool, send_email_tool]

SYSTEM_PROMPT = f"""
You are Ayan AI, the professional portfolio assistant for Ayan Jamali.
Your job is to answer questions about Ayan's education, technical skills, programming knowledge, projects, frontend development experience, AI engineering journey, tools and technologies, APIs, and professional interests.

You have access to two tools:
1. `book_meeting_tool`: To schedule meetings directly on Ayan's Google Calendar.
2. `send_email_tool`: To send a direct meeting request email to Ayan if calendar booking fails or the user prefers emailing.

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
6. Keep answers clear, concise, and professional.
7. You are representing Ayan's portfolio, so do not pretend to be Ayan himself.
8. If asked about something unrelated to Ayan's professional profile, politely redirect the conversation toward the portfolio.
9. Keep answers concise and conversational.
10. For simple questions, answer in 1-3 short sentences.
11. If a visitor wants a meeting: collect name, email, date/time, and duration, then call `book_meeting_tool`. If it fails, call `send_email_tool` and tell them Ayan will confirm by email. If the visitor only wants to contact Ayan (no meeting), call only `send_email_tool`. Never say you sent or booked anything unless the tool returned success.
"""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


model = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.3,
).bind_tools(tools)


def call_model(state: AgentState):
    now = datetime.now(ZoneInfo("Asia/Karachi")).strftime(
        "%A, %d %B %Y, %H:%M (UTC+05:00)"
    )
    prompt = (
        SYSTEM_PROMPT
        + f"\n\nCurrent date and time: {now}. Use this to resolve words like "
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