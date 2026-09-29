import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from agents.graph import ayan_agent

load_dotenv()

# creating FastAPI

app = FastAPI(
    title="Ayan AI portfolio API",
    description="backend API for Ayan's AI portfolio Assistant.",
    version="1.0.0"
)

# CORS Congig

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request to model..

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="User's message."
    )

    thread_id: str = Field(
        ...,
        min_length=1, 
        description="Unique conversation/thread ID"
    )
class ChatResponse(BaseModel):
    response: str
    thread_id: str

# Meeting Agent

class MeetingRequest(BaseModel):
    name: str  = Field(
        ..., 
        min_length=1, 
        max_length=100
    )
    email: str = Field(
        ..., 
        min_length=1,
        max_length=200         
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000
    )

class MeetingResponse(BaseModel):
    message: str


@app.get('/')
def root():
    return {
        "message": "Ayan AI Portfolio is running."
    }
@app.get("/health")
def health_chat():
    return{
        "status": "healthy"
    }

# Chat endpoint

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        config = {
            "configurable": {
                "thread_id": request.thread_id
            }
        }

        result = ayan_agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=request.message
                    )
                ]
            },
            config=config
        )

        response_message = result["messages"][-1]

        # Gemini/LangChain may return content as a list of blocks
        content = response_message.content

        if isinstance(content, list):
            text_parts = []

            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            response_text = "".join(text_parts).strip()

        else:
            response_text = str(content)

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id
        )
    except Exception as e:
        print("\n========== AGENT ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        print("=================================\n")

        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )

@app.post(
    "/meeting",
    response_model=MeetingResponse
)
def meeting(request: MeetingRequest):
    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(
            os.getenv("SMTP_PORT", "587")
        )
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        recipient_email = os.getenv(
            "MEETING_RECIPIENT_EMAIL"
        )

        if not all([
            smtp_host, smtp_password, smtp_host, smtp_port
        ]): 
            raise HTTPException(
                status_code=500, 
                detail="EMail service is not configured"
            )
        email_message = EmailMessage()
        email_message["subject"] = (
            f"New Porfolio Meeting Request from {request.name}"
        )

        email_message["From"] = smtp_username
        email_message["To"] = recipient_email
        email_message["Reply-To"] = request.email
        email_message.set_content(
            f"""
        New meeting request from your portfolio    

        Name: {request.name}
        Email: {request.email}
        Message: {request.message}

        you can directly reply to this email.
        """
)
        with smtplib.SMTP(
            smtp_host,
            smtp_port,
        ) as smtp:
            smtp.starttls()
            smtp.login(
                smtp_username,
                smtp_password
            )
            smtp.send_message(
                email_message
            )
        return MeetingResponse(
            message="Meeting request send succesfully."
        )
    except HTTPException:
        raise

    except Exception as e:
        print("\n EMAIL ERROR")
        print(type(e).__name__)
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail="Unable to send meeting request"
        )