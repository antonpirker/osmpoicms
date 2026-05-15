from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from osmpoicms.session import get_session

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/")
async def index(request: Request, error: str = ""):
    if get_session(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request, "landing.html", {"error": error})


@router.get("/dashboard")
async def dashboard(request: Request):
    session = get_session(request)
    if not session:
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "dashboard.html", {"user": session["user"]})
