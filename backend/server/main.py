from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from agents.graph import ayan_agent

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