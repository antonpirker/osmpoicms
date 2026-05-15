from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from osmpoicms.categories import CATEGORIES
from osmpoicms.session import get_session

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/")
async def index(request: Request, error: str = ""):
    if get_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    response = templates.TemplateResponse(request, "landing.html", {"error": error})
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
    return templates.TemplateResponse(
        request, "dashboard.html", {
            "user": session["user"],
            "categories": CATEGORIES,
            "prefill_community_id": community_id,
            "prefill_community_name": community_name,
            "prefill_category": category,
        }
    )
