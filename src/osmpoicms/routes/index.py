from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from osmpoicms.categories import CATEGORIES
from osmpoicms.i18n import get_t
from osmpoicms.session import get_session

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/")
async def index(request: Request, error: str = ""):
    if get_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    lang, t = get_t(request)
    response = templates.TemplateResponse(request, "landing.html", {"error": error, "t": t, "lang": lang})
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/dashboard")
async def dashboard(
    request: Request,
    community_id: str = "",
    community_name: str = "",
    category: str = "",
):
    session = get_session(request)
    if not session:
        return RedirectResponse("/")
    lang, t = get_t(request)
    return templates.TemplateResponse(
        request, "dashboard.html", {
            "user": session["user"],
            "categories": CATEGORIES,
            "prefill_community_id": community_id,
            "prefill_community_name": community_name,
            "prefill_category": category,
            "t": t,
            "lang": lang,
            "lang_next": request.url.path,
        }
    )


@router.get("/set-lang")
async def set_lang(request: Request, lang: str = "en", next: str = "/dashboard"):
    if lang not in {"en", "de"}:
        lang = "en"
    if not next.startswith("/"):
        next = "/dashboard"
    response = RedirectResponse(next, status_code=302)
    response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="lax")
    return response
