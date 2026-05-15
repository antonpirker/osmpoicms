import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from osmpoicms.categories import get_columns
from osmpoicms.i18n import all_translations, get_t
from osmpoicms.osm_write import (
    apply_tag_changes,
    close_changeset,
    create_changeset,
    fetch_element_xml,
    put_element,
)
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

    lang, t = get_t(request)

    return templates.TemplateResponse(request, "poi_table.html", {
        "user": session["user"],
        "community_id": community_id,
        "community_name": community_name,
        "category": category,
        "pois": pois,
        "columns": get_columns(category),
        "poi_count": len(pois),
        "limited": len(pois) == 200,
        "error": error,
        "t": t,
        "lang": lang,
        "all_translations": all_translations(),
    })


@router.post("/confirm")
async def confirm_pois(request: Request):
    session = get_session(request)
    if not session:
        return RedirectResponse("/", status_code=302)

    form = await request.form()
    category = form.get("category", "")
    col_keys = [key for key, _ in get_columns(category)]
    poi_count = int(form.get("poi_count", 0))

    changed = []
    for i in range(poi_count):
        etype = form.get(f"poi_type_{i}")
        eid = form.get(f"poi_id_{i}")
        all_tags = json.loads(form.get(f"poi_all_tags_{i}", "{}"))

        new_tags = {key: form.get(f"edit_{i}_{key}", "") for key in col_keys}
        orig_tags = {key: form.get(f"orig_{i}_{key}", "") for key in col_keys}

        diff = []
        for key in col_keys:
            orig, new = orig_tags[key], new_tags[key]
            if new == orig:
                continue
            if orig == "" and new != "":
                diff.append({"op": "add", "key": key, "old": None, "new": new})
            elif new == "":
                diff.append({"op": "del", "key": key, "old": orig, "new": None})
            else:
                diff.append({"op": "upd", "key": key, "old": orig, "new": new})

        if diff:
            changed.append({
                "type": etype,
                "id": eid,
                "name": all_tags.get("name", f"{etype}/{eid}"),
                "diff": diff,
                # Passed as hidden fields to /pois/save
                "all_tags_json": form.get(f"poi_all_tags_{i}"),
                "new_tags_json": json.dumps(new_tags),
            })

    lang, t = get_t(request)
    return templates.TemplateResponse(request, "poi_confirm.html", {
        "user": session["user"],
        "community_id": form.get("community_id"),
        "community_name": form.get("community_name"),
        "category": category,
        "changed": changed,
        "t": t,
        "lang": lang,
    })


@router.post("/save")
async def save_pois(request: Request):
    session = get_session(request)
    if not session:
        return RedirectResponse("/", status_code=302)

    form = await request.form()
    comment = form.get("comment", "").strip()[:255]
    source = form.get("source", "").strip()[:255]
    change_count = int(form.get("change_count", 0))
    token = session["access_token"]

    changeset_id = await create_changeset(token, comment, source)

    results = []
    for j in range(change_count):
        etype = form.get(f"c_type_{j}")
        eid = int(form.get(f"c_id_{j}"))
        new_tags = json.loads(form.get(f"c_new_tags_{j}", "{}"))
        name = new_tags.get("name") or form.get(f"c_name_{j}", f"{etype}/{eid}")

        try:
            xml = await fetch_element_xml(token, etype, eid)
            updated_xml, _ = apply_tag_changes(xml, new_tags, changeset_id)
            try:
                await put_element(token, etype, eid, updated_xml)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    # Version conflict — refetch and retry once
                    xml = await fetch_element_xml(token, etype, eid)
                    updated_xml, _ = apply_tag_changes(xml, new_tags, changeset_id)
                    await put_element(token, etype, eid, updated_xml)
                else:
                    raise
            results.append({"name": name, "type": etype, "id": eid, "ok": True})
        except Exception as e:
            results.append({"name": name, "type": etype, "id": eid, "ok": False, "error": str(e)})

    await close_changeset(token, changeset_id)

    lang, t = get_t(request)
    return templates.TemplateResponse(request, "poi_success.html", {
        "user": session["user"],
        "changeset_id": changeset_id,
        "results": results,
        "community_id": form.get("community_id"),
        "community_name": form.get("community_name"),
        "category": form.get("category"),
        "t": t,
        "lang": lang,
    })
