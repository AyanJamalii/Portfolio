"""Google OAuth credentials and the Calendar API client."""

import json
import os
import threading

from fastapi import HTTPException
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .config import GOOGLE_SCOPES, TOKEN_PATH

print("Google token path:", TOKEN_PATH.resolve(), "exists:", TOKEN_PATH.exists())

_lock = threading.Lock()
_cached_creds: Credentials | None = None


def token_comes_from_env() -> bool:
    """True in production, where the token is stored in GOOGLE_TOKEN_JSON_CONTENT."""
    return bool(os.getenv("GOOGLE_TOKEN_JSON_CONTENT"))


def create_google_flow(state=None) -> Flow:
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return flow


def reset_credentials_cache():
    """Forget the cached credentials (call after saving a new token)."""
    global _cached_creds
    with _lock:
        _cached_creds = None


def _load_credentials() -> Credentials:
    token_json = os.getenv("GOOGLE_TOKEN_JSON_CONTENT")
    try:
        if token_json:
            return Credentials.from_authorized_user_info(json.loads(token_json), GOOGLE_SCOPES)
        if TOKEN_PATH.exists():
            return Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
    except (ValueError, KeyError) as e:
        print(f"Token load error: {type(e).__name__}: {e}")
        raise HTTPException(500, "Stored Google token is invalid.") from e

    raise HTTPException(401, "Google Calendar has not been connected yet.")


def get_calendar_service():
    global _cached_creds
    with _lock:
        if _cached_creds is None:
            _cached_creds = _load_credentials()
        creds = _cached_creds

        if not creds.valid:
            if not creds.refresh_token:
                _cached_creds = None
                raise HTTPException(401, "Google authorization expired. Reconnect Calendar.")
            try:
                creds.refresh(GoogleRequest())
            except RefreshError as e:
                _cached_creds = None
                print(f"Token refresh failed: {e}")
                raise HTTPException(401, "Google authorization expired. Reconnect Calendar.") from e

            if not token_comes_from_env():
                try:
                    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
                except OSError as e:
                    print(f"Could not save refreshed token: {e}")

    return build("calendar", "v3", credentials=creds, cache_discovery=False)
