"""Small input-cleaning helpers."""

import re

from fastapi import HTTPException

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please provide a valid email address.")
    return email


def clean_text(value: str) -> str:
    return " ".join(value.split())
