"""Sending emails to Ayan through Resend."""

import os

import requests
from fastapi import HTTPException

from .utils import clean_text


def send_email(subject: str, body: str, reply_to: str | None = None):
    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("MEETING_RECIPIENT_EMAIL")
    if not api_key or not recipient:
        raise HTTPException(500, "Email service is not configured properly.")

    payload = {
        "from": "Portfolio <onboarding@resend.dev>",
        "to": [recipient],
        "subject": clean_text(subject)[:200],
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
        raise RuntimeError(f"Resend error {r.status_code}: {r.text}")
