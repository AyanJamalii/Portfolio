from fastapi import APIRouter, HTTPException

from ..email_service import send_email
from ..schemas import MeetingRequest, MeetingResponse
from ..utils import clean_email, clean_text

router = APIRouter()


@router.post("/meeting", response_model=MeetingResponse)
def meeting(request: MeetingRequest):
    name = clean_text(request.name)
    email = clean_email(request.email)
    message = request.message.strip()
    if not name or not message:
        raise HTTPException(400, "Name and message cannot be empty.")

    try:
        send_email(
            subject=f"New Portfolio Message from {name}",
            body=(
                "New message from your portfolio:\n\n"
                f"Name: {name}\nEmail: {email}\n"
                f"Message: {message}\n"
            ),
            reply_to=email,
        )
        return MeetingResponse(message="Meeting request sent successfully.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Email Error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Unable to send meeting request.") from e
