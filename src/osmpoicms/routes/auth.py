import base64
import hashlib
import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from osmpoicms.config import settings
from osmpoicms.session import clear_session, set_session

router = APIRouter(prefix="/auth")

_AUTH_URL = "https://www.openstreetmap.org/oauth2/authorize"
_TOKEN_URL = "https://www.openstreetmap.org/oauth2/token"
_OSM_API = "https://api.openstreetmap.org/api/0.6"

_PKCE_COOKIE = "pkce"
_PKCE_MAX_AGE = 600  # 10 minutes


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


@router.get("/login")
async def login():
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    auth_url = _AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": settings.osm_client_id,
        "redirect_uri": settings.osm_redirect_uri,
        "response_type": "code",
        "scope": "read_prefs write_api",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })

    s = URLSafeTimedSerializer(settings.session_secret)
    response = RedirectResponse(auth_url)
    response.set_cookie(
        _PKCE_COOKIE,
        s.dumps({"verifier": verifier, "state": state}),
        max_age=_PKCE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/callback")
async def callback(request: Request, code: str, state: str):
    s = URLSafeTimedSerializer(settings.session_secret)
    pkce_cookie = request.cookies.get(_PKCE_COOKIE)
    if not pkce_cookie:
        return RedirectResponse("/?error=auth_failed")
    try:
        pkce = s.loads(pkce_cookie, max_age=_PKCE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return RedirectResponse("/?error=auth_failed")

    if pkce["state"] != state:
        return RedirectResponse("/?error=auth_failed")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "redirect_uri": settings.osm_redirect_uri,
                "code": code,
                "code_verifier": pkce["verifier"],
            },
            auth=(settings.osm_client_id, settings.osm_client_secret),
        )
        if not r.is_success:
            return RedirectResponse("/?error=auth_failed")
        access_token = r.json()["access_token"]

        r = await client.get(
            f"{_OSM_API}/user/details.json",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not r.is_success:
            return RedirectResponse("/?error=auth_failed")
        user = r.json()["user"]

    response = RedirectResponse("/dashboard")
    response.delete_cookie(_PKCE_COOKIE)
    set_session(response, {
        "access_token": access_token,
        "user": {"id": user["id"], "display_name": user["display_name"]},
    })
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/")
    clear_session(response)
    return response
