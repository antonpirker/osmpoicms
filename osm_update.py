#!/usr/bin/env python3
"""
Aktualisiert OSM-Elemente aus einer TSV-Datei.

Einmalig: OAuth2-App auf osm.org registrieren
  -> My Settings -> OAuth2 Applications -> Register new application
  -> Redirect URI: http://127.0.0.1:8765/callback
  -> Scopes: read_prefs, write_api
  -> Client Secret leer lassen (Public Client)
  -> Client ID in CLIENT_ID unten eintragen

Verwendung:
  python3 osm_update.py restaurants.tsv
"""

import csv
import sys
import os
import json
import hashlib
import base64
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from xml.sax.saxutils import escape

# ── Konfiguration ────────────────────────────────────────────────────────────
CLIENT_ID     = "6pRCTVHA1z2g0JJq14_LiK_5WKqcrP-co1IR28IMh3w"
CLIENT_SECRET = "LKEvz33KkVSqkk0b6wB-fEMHchi2QdtA56uy1pYaWcs"          # <- Client Secret hier eintragen
REDIRECT_URI = "http://127.0.0.1:8765/callback"
TOKEN_FILE   = Path("~/.config/osm-updater/token.json").expanduser()
OSM_API      = "https://api.openstreetmap.org/api/0.6"
AUTH_URL     = "https://www.openstreetmap.org/oauth2/authorize"
TOKEN_URL    = "https://www.openstreetmap.org/oauth2/token"
SCOPES       = "read_prefs write_api"
# ─────────────────────────────────────────────────────────────────────────────

LEGACY_TAGS  = {"contact:email", "contact:phone", "contact:website", "url"}
SKIP_COLUMNS = {"type", "id"}


# ── OAuth2 PKCE ──────────────────────────────────────────────────────────────

def _pkce_pair() -> tuple[str, str]:
    verifier  = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _wait_for_code(port: int = 8765) -> str:
    """Startet einen lokalen HTTP-Server und wartet bis ein Auth-Code ankommt."""
    code_holder = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code = params.get("code", [None])[0]
            if code:
                code_holder["code"] = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if code:
                self.wfile.write(
                    b"<h2>Authentifizierung erfolgreich &#10003;</h2>"
                    b"<p>Du kannst diesen Tab schlie&szlig;en.</p>"
                )

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    # Anfragen abarbeiten bis ein Code da ist (Browser macht oft mehrere Requests)
    while not code_holder.get("code"):
        server.handle_request()
    return code_holder["code"]


def authenticate() -> str:
    """Führt OAuth2 PKCE Flow durch und gibt Bearer Token zurück."""
    if not CLIENT_ID:
        print("Fehler: CLIENT_ID ist nicht gesetzt. Bitte in osm_update.py eintragen.")
        sys.exit(1)

    # Gespeichertes Token verwenden falls vorhanden
    if TOKEN_FILE.exists():
        token = json.loads(TOKEN_FILE.read_text())["access_token"]
        print("Gespeichertes Token verwendet.")
        return token

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    params = urllib.parse.urlencode({
        "client_id":             CLIENT_ID,
        "redirect_uri":          REDIRECT_URI,
        "response_type":         "code",
        "scope":                 SCOPES,
        "state":                 state,
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTH_URL}?{params}"

    print("Browser wird geöffnet für OSM-Login...")
    webbrowser.open(auth_url)

    code = _wait_for_code()
    if not code:
        print("Fehler: Kein Auth-Code empfangen.")
        sys.exit(1)

    # Code gegen Token tauschen
    r = requests.post(TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "redirect_uri":  REDIRECT_URI,
            "code":          code,
            "code_verifier": verifier,
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
    )
    if not r.ok:
        print(f"Token-Austausch fehlgeschlagen ({r.status_code}):\n{r.text}")
        sys.exit(1)
    token_data = r.json()

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(token_data))
    print(f"Token gespeichert: {TOKEN_FILE}")

    return token_data["access_token"]


# ── OSM API ──────────────────────────────────────────────────────────────────

def get_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    s.headers["User-Agent"]    = "osm-bulk-updater/1.0"
    return s


def create_changeset(session: requests.Session, comment: str, source: str) -> str:
    xml = (
        "<osm><changeset>"
        f'<tag k="comment" v="{escape(comment)}"/>'
        f'<tag k="source" v="{escape(source)}"/>'
        '<tag k="created_by" v="osm-bulk-updater/1.0"/>'
        "</changeset></osm>"
    )
    r = session.put(
        f"{OSM_API}/changeset/create",
        data=xml.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
    )
    if not r.ok:
        print(f"Changeset-Erstellung fehlgeschlagen ({r.status_code}):\n{r.text}")
        sys.exit(1)
    return r.text.strip()


def close_changeset(session: requests.Session, changeset_id: str) -> None:
    session.put(f"{OSM_API}/changeset/{changeset_id}/close")


def fetch_element(session: requests.Session, etype: str, eid: str) -> str:
    r = session.get(f"{OSM_API}/{etype}/{eid}")
    r.raise_for_status()
    return r.text


def apply_updates(xml_str: str, tsv_row: dict, changeset_id: str) -> tuple[str, list]:
    root    = ET.fromstring(xml_str)
    element = root[0]
    element.set("changeset", changeset_id)

    existing = {t.get("k"): t for t in element.findall("tag")}
    changes  = []

    for legacy in LEGACY_TAGS:
        if legacy in existing:
            element.remove(existing.pop(legacy))
            changes.append(f"  DEL  {legacy}")

    for col, val in tsv_row.items():
        if col in SKIP_COLUMNS or col in LEGACY_TAGS:
            continue
        val = val.strip()
        if not val:
            continue
        if col in existing:
            old = existing[col].get("v")
            if old != val:
                existing[col].set("v", val)
                changes.append(f"  UPD  {col}: {old!r} -> {val!r}")
        else:
            tag = ET.SubElement(element, "tag")
            tag.set("k", col)
            tag.set("v", val)
            changes.append(f"  ADD  {col}: {val!r}")

    xml_out = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_out}', changes


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python3 osm_update.py <datei.tsv>")
        sys.exit(1)

    tsv_path = sys.argv[1]
    token    = authenticate()
    session  = get_session(token)

    comment = input("Changeset-Kommentar: ").strip()
    source  = input("Source: ").strip()
    if not comment:
        print("Kommentar darf nicht leer sein.")
        sys.exit(1)

    with open(tsv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    rows_by_key = {(r["type"], r["id"]): r for r in rows}

    print(f"\n{len(rows)} Elemente gefunden. Vorschau der Änderungen:\n")

    previews = []
    for row in rows:
        etype, eid = row["type"], row["id"]
        label = f"{etype}/{eid} ({row.get('name', '')})"
        try:
            xml_str = fetch_element(session, etype, eid)
            _, changes = apply_updates(xml_str, row, "PREVIEW")
            previews.append((etype, eid, row.get("name", ""), changes, xml_str))
            if changes:
                print(f"{label}:")
                print("\n".join(changes))
            else:
                print(f"{label}: keine Änderungen")
        except requests.HTTPError as e:
            print(f"FEHLER beim Abrufen von {label}: {e}")
            previews.append((etype, eid, row.get("name", ""), None, None))

    total = sum(len(p[3]) for p in previews if p[3])
    print(f"\nGesamt: {total} Tag-Änderungen an {sum(1 for p in previews if p[3])} Elementen.")

    if input("\nÄnderungen in OSM schreiben? [j/N] ").strip().lower() != "j":
        print("Abgebrochen.")
        sys.exit(0)

    changeset_id = create_changeset(session, comment, source)
    print(f"\nChangeset: https://www.openstreetmap.org/changeset/{changeset_id}\n")

    ok = failed = 0
    for etype, eid, name, changes, xml_str in previews:
        label = f"{etype}/{eid} ({name})"
        if xml_str is None:
            print(f"SKIP  {label} (Abruf fehlgeschlagen)")
            failed += 1
            continue
        if not changes:
            print(f"SKIP  {label} (keine Änderungen)")
            continue

        updated_xml, _ = apply_updates(xml_str, rows_by_key[(etype, eid)], changeset_id)
        try:
            r = session.put(
                f"{OSM_API}/{etype}/{eid}",
                data=updated_xml.encode("utf-8"),
                headers={"Content-Type": "text/xml"},
            )
            r.raise_for_status()
            print(f"OK    {label} (Version {r.text.strip()})")
            ok += 1
        except requests.HTTPError as e:
            print(f"FEHLER {label}: {e}\n{e.response.text}")
            failed += 1

    close_changeset(session, changeset_id)
    print(f"\nFertig. {ok} aktualisiert, {failed} Fehler.")
    print(f"Changeset: https://www.openstreetmap.org/changeset/{changeset_id}")


if __name__ == "__main__":
    main()
