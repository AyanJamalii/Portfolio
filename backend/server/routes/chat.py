from fastapi import APIRouter, HTTPException
from fastapi import Request as FastAPIRequest
from langchain_core.messages import HumanMessage

from agents.graph import ayan_agent

from ..config import CHAT_LIMIT, CHAT_WINDOW_SECONDS
from ..rate_limit import rate_limit
from ..schemas import ChatRequest, ChatResponse

router = APIRouter()


def _extract_text(content) -> str:
    """The model may return a plain string or a list of content blocks."""
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return str(content).strip()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: FastAPIRequest):
    rate_limit(http_request, "chat", CHAT_LIMIT, CHAT_WINDOW_SECONDS)
    try:
        result = ayan_agent.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config={"configurable": {"thread_id": request.thread_id}},
        )
        response_text = _extract_text(result["messages"][-1].content)
        if not response_text:
            response_text = "Sorry, I didn't catch that. Could you rephrase?"
        return ChatResponse(response=response_text, thread_id=request.thread_id)

    except Exception as e:
        print(f"Agent Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="The AI assistant is temporarily unavailable.",
        ) from e
