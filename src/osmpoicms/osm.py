import httpx

_PHOTON_URL = "https://photon.komoot.io/api/"

# Austria bounding box (lon_min, lat_min, lon_max, lat_max)
_AUSTRIA_BBOX = "9.5,46.3,17.2,49.0"


async def search_communities(q: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            _PHOTON_URL,
            params={
                "q": q,
                "limit": 20,
                "lang": "de",
                "bbox": _AUSTRIA_BBOX,
                "osm_tag": "boundary:administrative",
            },
            timeout=10,
        )
        r.raise_for_status()

    results = []
    for f in r.json().get("features", []):
        props = f.get("properties", {})
        if props.get("osm_type") != "R":
            continue
        if props.get("country_code", "").lower() != "at":
            continue
        name = props.get("name", "")
        if not name:
            continue
        state = props.get("state", "")
        display = f"{name} ({state})" if state else name
        results.append({"id": props["osm_id"], "name": display})

    results.sort(key=lambda x: x["name"].lower())
    return results[:8]
