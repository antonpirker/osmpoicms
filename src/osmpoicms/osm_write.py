import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import httpx

_OSM_API = "https://api.openstreetmap.org/api/0.6"
_LEGACY_TAGS = {"contact:email", "contact:phone", "contact:website", "url"}


def apply_tag_changes(
    xml_str: str, new_tags: dict[str, str], changeset_id: str
) -> tuple[str, list[dict]]:
    """Apply new_tags to the OSM element XML. Empty string = delete tag.
    Tags not in new_tags are preserved unchanged.
    Returns updated XML and a list of change dicts."""
    root = ET.fromstring(xml_str)
    element = root[0]
    element.set("changeset", changeset_id)

    existing = {t.get("k"): t for t in element.findall("tag")}
    changes = []

    for legacy in _LEGACY_TAGS:
        if legacy in existing:
            element.remove(existing.pop(legacy))

    for key, val in new_tags.items():
        if key in existing:
            old = existing[key].get("v")
            if val == "":
                element.remove(existing[key])
                changes.append({"op": "del", "key": key, "old": old})
            elif old != val:
                existing[key].set("v", val)
                changes.append({"op": "upd", "key": key, "old": old, "new": val})
        elif val != "":
            tag = ET.SubElement(element, "tag")
            tag.set("k", key)
            tag.set("v", val)
            changes.append({"op": "add", "key": key, "new": val})

    xml_out = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_out}', changes


async def create_changeset(token: str, comment: str, source: str) -> str:
    xml = (
        "<osm><changeset>"
        f'<tag k="comment" v="{escape(comment)}"/>'
        f'<tag k="source" v="{escape(source)}"/>'
        '<tag k="created_by" v="osmpoicms/1.0"/>'
        "</changeset></osm>"
    )
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{_OSM_API}/changeset/create",
            content=xml.encode("utf-8"),
            headers={"Content-Type": "text/xml", "Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
    return r.text.strip()


async def close_changeset(token: str, changeset_id: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{_OSM_API}/changeset/{changeset_id}/close",
            headers={"Authorization": f"Bearer {token}"},
        )


async def fetch_element_xml(token: str, etype: str, eid: int) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_OSM_API}/{etype}/{eid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
    return r.text


async def put_element(token: str, etype: str, eid: int, xml: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{_OSM_API}/{etype}/{eid}",
            content=xml.encode("utf-8"),
            headers={"Content-Type": "text/xml", "Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
    return r.text.strip()
