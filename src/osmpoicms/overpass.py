import httpx

from osmpoicms.categories import CATEGORY_TAGS

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "osmpoicms/1.0 (anton@maptoolkit.com)"}


# Categories where private/members-only POIs should be excluded
_FILTER_PRIVATE = {"leisure", "huts"}


def _build_query(area_id: int, tags: list[tuple[str, str]], filter_private: bool = False) -> str:
    access_filter = '["access"!="private"]' if filter_private else ""
    statements = "\n".join(
        f'  {etype}["{k}"]{access_filter}(area.searchArea);'
        if v == "*" else
        f'  {etype}["{k}"="{v}"]{access_filter}(area.searchArea);'
        for k, v in tags
        for etype in ("node", "way", "relation")
    )
    return (
        f"[out:json][timeout:30];\n"
        f"area(id:{area_id})->.searchArea;\n"
        f"(\n{statements}\n);\n"
        f"out center 200;"
    )


async def fetch_pois(relation_id: int, category: str) -> list[dict]:
    tags = CATEGORY_TAGS[category]
    area_id = relation_id + 3_600_000_000
    query = _build_query(area_id, tags, filter_private=category in _FILTER_PRIVATE)

    async with httpx.AsyncClient() as client:
        r = await client.post(
            _OVERPASS_URL,
            data={"data": query},
            headers=_HEADERS,
            timeout=40,
        )
        r.raise_for_status()

    pois = [
        {
            "type": el["type"],
            "id": el["id"],
            "tags": el.get("tags", {}),
            "lat": el.get("lat") or el.get("center", {}).get("lat"),
            "lon": el.get("lon") or el.get("center", {}).get("lon"),
        }
        for el in r.json().get("elements", [])
    ]
    return sorted(pois, key=lambda p: (0, p["tags"]["name"].lower()) if p["tags"].get("name") else (1, ""))
