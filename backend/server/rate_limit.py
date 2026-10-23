"""A tiny in-memory rate limiter (per client IP)."""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException
from fastapi import Request as FastAPIRequest

_hits: dict = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: FastAPIRequest) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: FastAPIRequest, bucket: str, limit: int, window: int):
    now = time.monotonic()
    key = (bucket, client_ip(request))
    with _lock:
        hits = _hits[key]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Too many requests. Please slow down.")
        hits.append(now)
