import httpx

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "osmpoicms/1.0 (anton@maptoolkit.com)"}


async def search_communities(q: str) -> list[dict]:
    # Search directly in Overpass for Austrian administrative boundaries by name.
    # Nominatim is unreliable for this — it returns person names and addresses
    # before actual Gemeinden when the query matches common words like "Maria".
    query = f"""
[out:json][timeout:10];
area["ISO3166-1"="AT"][admin_level=2]->.at;
relation["boundary"="administrative"]["admin_level"~"^(6|8|9)$"]["name"~"{q}",i](area.at);
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
        [{"id": el["id"], "name": el["tags"].get("name", "")} for el in elements],
        key=lambda x: x["name"].lower(),
    )
    return results[:8]
