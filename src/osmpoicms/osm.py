import httpx

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "osmpoicms/1.0 (anton@maptoolkit.com)"}

# Overpass area ID for Austria (derived from OSM relation 16239 → +3600000000)
_AUSTRIA_AREA_ID = 3600016239

_LEVEL_LABEL = {"6": "Bezirk", "8": "Gemeinde", "9": "Ortschaft"}


def _display(el: dict) -> str:
    tags = el["tags"]
    name = tags.get("name", "")
    parts = []
    state = tags.get("is_in:state") or tags.get("addr:state")
    if state:
        parts.append(state)
    level = _LEVEL_LABEL.get(tags.get("admin_level", ""))
    if level:
        parts.append(level)
    return f"{name} ({', '.join(parts)})" if parts else name


async def search_communities(q: str) -> list[dict]:
    # Search directly in Overpass for Austrian administrative boundaries by name.
    # Nominatim is unreliable for this — it returns person names and addresses
    # before actual Gemeinden when the query matches common words like "Maria".
    query = f"""
[out:json][timeout:10];
relation["boundary"="administrative"]["admin_level"~"^(6|8|9)$"]["name"~"{q}",i](area:{_AUSTRIA_AREA_ID});
out tags 8;
"""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            _OVERPASS_URL,
            data={"data": query},
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()

    elements = r.json().get("elements", [])
    results = sorted(
        [{"id": el["id"], "name": _display(el)} for el in elements],
        key=lambda x: x["name"].lower(),
    )
    return results[:8]
