"""Ayan AI Portfolio API. Run with:  uvicorn server.main:app --reload  (from the backend folder)."""

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routes import booking, chat, health, meeting, oauth

app = FastAPI(
    title="Ayan AI Portfolio API",
    description="Backend API for Ayan's AI portfolio assistant.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (health.router, chat.router, meeting.router, booking.router, oauth.router):
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
