"""Google OAuth sign-in. Only meant for local use, to create google_token.json."""

import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..config import TOKEN_PATH
from ..google_auth import create_google_flow, reset_credentials_cache, token_comes_from_env

router = APIRouter(prefix="/oauth")


def _oauth_allowed():
    # In production the token comes from an env variable, so these routes are
    # switched off. Nobody can replace your calendar connection.
    if token_comes_from_env():
        raise HTTPException(404, "Not found.")


@router.get("/start")
def oauth_start():
    _oauth_allowed()
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(500, "Google OAuth is not configured.")

    flow = create_google_flow()
    url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return RedirectResponse(url)


@router.get("/callback")
def oauth_callback(code: str = Query(...), state: str = Query(...)):
    _oauth_allowed()
    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(code=code)

        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(flow.credentials.to_json(), encoding="utf-8")
        reset_credentials_cache()

        print("Token saved to:", TOKEN_PATH.resolve())
        return {
            "status": "connected",
            "message": "Google Calendar authorization saved successfully!",
            "saved_to": str(TOKEN_PATH.resolve()),
        }
    except Exception as e:
        print(f"Google OAuth Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Google authorization failed: {e!s}",
        ) from e
