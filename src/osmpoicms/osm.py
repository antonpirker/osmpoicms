import httpx

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "osmpoicms/1.0 (anton@maptoolkit.com)"}


async def search_communities(q: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            _NOMINATIM_URL,
            params={
                "q": q,
                "format": "jsonv2",
                "countrycodes": "at",
                "limit": 20,
                "addressdetails": 1,
                "namedetails": 1,
            },
            headers=_HEADERS,
            timeout=10,
        )
        r.raise_for_status()

    results = []
    for el in r.json():
        if el.get("osm_type") != "relation":
            continue
        if el.get("class") != "boundary" or el.get("type") != "administrative":
            continue
        name = el.get("namedetails", {}).get("name", "")
        if not name:
            continue
        addr = el.get("address", {})
        state = addr.get("state", "")
        display = f"{name} ({state})" if state else name
        results.append({"id": el["osm_id"], "name": display})

    results.sort(key=lambda x: x["name"].lower())
    return results[:8]
