from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from osmpoicms.config import settings

_COOKIE = "session"
_MAX_AGE = 90 * 24 * 3600  # 90 days


def _s() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret)


def get_session(request: Request) -> dict | None:
    cookie = request.cookies.get(_COOKIE)
    if not cookie:
        return None
    try:
        return _s().loads(cookie, max_age=_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def set_session(response: Response, data: dict) -> None:
    response.set_cookie(
        _COOKIE,
        _s().dumps(data),
        max_age=_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(_COOKIE)
