"""Cancel codes: only the person who booked a meeting can cancel it.

A random code is created at booking time and shown to the visitor (in the chat reply and
in their calendar invite). Cancelling needs the email AND the code, and wrong guesses are
limited per email.
"""

import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

# No look-alike characters (0/O, 1/I/L)
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6

MAX_FAILED_ATTEMPTS = 5
FAILURE_WINDOW_SECONDS = 3600

_failures: dict = defaultdict(deque)
_lock = threading.Lock()


def new_cancel_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(CODE_LENGTH))


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def codes_match(stored: str | None, given: str) -> bool:
    if not stored:
        return False
    return hmac.compare_digest(_normalize(stored).encode(), _normalize(given).encode())


def _purge(key: str, now: float):
    attempts = _failures[key]
    while attempts and now - attempts[0] > FAILURE_WINDOW_SECONDS:
        attempts.popleft()


def check_not_locked(key: str):
    """Raise 429 if there were too many wrong codes for this email recently."""
    with _lock:
        _purge(key, time.monotonic())
        if len(_failures[key]) >= MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                429,
                "TOO_MANY_ATTEMPTS: Too many wrong cancel codes for this email. "
                "The visitor can leave a message for Ayan instead.",
            )


def record_failure(key: str):
    with _lock:
        _failures[key].append(time.monotonic())


def clear_failures(key: str):
    with _lock:
        _failures.pop(key, None)
