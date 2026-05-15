from pathlib import Path

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from osmpoicms.categories import CATEGORIES, get_columns
from osmpoicms.overpass import fetch_pois
from osmpoicms.session import get_session

router = APIRouter(prefix="/pois")
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.post("")
async def show_pois(
    request: Request,
    community_id: int = Form(...),
    community_name: str = Form(...),
    category: str = Form(...),
):
    session = get_session(request)
    if not session:
        return RedirectResponse("/", status_code=302)

    error = None
    pois = []
    try:
        pois = await fetch_pois(community_id, category)
    except httpx.TimeoutException:
        error = "Overpass API timed out. Please try again."
    except Exception:
        error = "Failed to load POIs. Please try again."

    category_label = next((label for val, label in CATEGORIES if val == category), category)

    return templates.TemplateResponse(request, "poi_table.html", {
        "user": session["user"],
        "community_id": community_id,
        "community_name": community_name,
        "category": category,
        "category_label": category_label,
        "pois": pois,
        "columns": get_columns(category),
        "poi_count": len(pois),
        "limited": len(pois) == 200,
        "error": error,
    })
