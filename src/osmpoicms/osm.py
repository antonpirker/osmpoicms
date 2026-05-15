import httpx

_NOMINATIM = "https://nominatim.openstreetmap.org"
_HEADERS = {"User-Agent": "osmpoicms/1.0 (anton@maptoolkit.com)"}


async def search_communities(q: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_NOMINATIM}/search",
            params={
                "q": q,
                "countrycodes": "at",
                "format": "jsonv2",
                "limit": 15,
                "extratags": 1,
            },
            headers=_HEADERS,
            timeout=10,
        )
        r.raise_for_status()

    # 6: Statutarstädte (Innsbruck, Graz, Salzburg, Wien, ...)
    # 8: regular Gemeinden
    # 9: Stadtbezirke (e.g. Vienna's 23 districts)
    return [
        {"id": item["osm_id"], "name": item["display_name"].split(",")[0].strip()}
        for item in r.json()
        if item.get("osm_type") == "relation"
        and item.get("extratags", {}).get("admin_level") in ("6", "8", "9")
    ][:5]
