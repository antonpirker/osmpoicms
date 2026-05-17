import asyncio

import httpx

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "osmpoicms/1.0 (anton@maptoolkit.com)"}

_cache: list[dict] | None = None
_cache_lock = asyncio.Lock()

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


async def _load_cache() -> None:
    global _cache
    query = """
[out:json][timeout:60];
area["ISO3166-1"="AT"][admin_level=2]->.at;
relation["boundary"="administrative"]["admin_level"~"^(6|8|9)$"](area.at);
out tags;
"""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            _OVERPASS_URL,
            data={"data": query},
            headers=_HEADERS,
            timeout=90,
        )
        r.raise_for_status()

    elements = r.json().get("elements", [])
    _cache = sorted(
        [{"id": el["id"], "name": _display(el)} for el in elements],
        key=lambda x: x["name"].lower(),
    )


async def search_communities(q: str) -> list[dict]:
    global _cache
    async with _cache_lock:
        if _cache is None:
            await _load_cache()

    q_lower = q.lower()
    results = [c for c in _cache if q_lower in c["name"].lower()]
    return results[:8]
