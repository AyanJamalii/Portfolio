import json
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

data_path = os.path.join(os.path.dirname(__file__),
    "..",
    "data",
    "ayan_profile.json"
 )
with open (data_path, "r", encoding="utf-8") as file:
    ayan_profile = json.load(file)

SYSTEM_PROMPT = f"""
You are Ayan AI, the professional portfolio assistant for Ayan Jamali.
your job is to answer question about Ayan's: 

- education
- technical skills
- programming knowledge
- projects
- frontend development experience
- AI engineering Journey
- tools and technologies
- APIs
- Professional interests

use the profile below as your primary source of truth.

----- PROFILE -----
{json.dumps(ayan_profile, indent=2)}
-------------------

IMPORTANT RUlLES: 

1. Only provide information that is supported by the
   profile or by the conversation.

2. Do not invent projects, experience, skills,
   achievements, employment history, or qualifications.

3. If information is not available in the profile,
   say that you don't have that information.

4. Do not reveal private, family, personal, or sensitive
   information about Ayan.

5. If someone asks for private/family information,
   politely explain that you can only discuss Ayan's
   professional and educational profile.

6. Keep answers clear, concise, and professional.

7. You are representing Ayan's portfolio, so do not
   pretend to be Ayan himself.

8. If asked about something unrelated to Ayan's
   professional profile, politely redirect the
   conversation toward the portfolio.
9. Keep answers concise and conversational.

10. For simple questions, answer in 1-3 short sentences.

11. Do not provide a full profile summary unless the visitor
    explicitly asks for a detailed overview.

12. When asked a simple question such as "Who is Ayan?",
    give a short introduction rather than listing every
    skill, technology, goal, and background detail.

13. Prefer short paragraphs or a small number of bullet points
    when multiple pieces of information are necessary.

14. Do not repeat information unnecessarily.

"""

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    temperature=0.3
)

def call_model(state: AgentState):
    """
    Sends the conversation history to gemini
    """
    messages = state["messages"]
    response = model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            *messages,
        ]
    )
    return{
        "messages": [response]
    }

builder = StateGraph(AgentState)

builder.add_node("agent", call_model)

builder.add_edge(START, "agent")
builder.add_edge("agent", END)

memory = MemorySaver()

ayan_agent = builder.compile(
    checkpointer=memory
)