# OSM POI CMS — Plan

A web app for Austrian municipalities to manage and review local POI data on OpenStreetMap.

---

## Goals

- Let OSM-authenticated users select their Austrian community (Gemeinde, OSM admin_level=8)
- Show POIs for that community by category (one category at a time, max 200)
- Edit POI tags inline and push changes back to OSM via the API

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Runtime | Python 3.12 via pyenv | `.python-version` managed by pyenv |
| Env | direnv + `.envrc` | auto-loads venv, secrets |
| Packages | uv | `uv sync`, `uv add` |
| Linting/Format | ruff | replaces black + flake8 |
| Web framework | FastAPI | async, modern, good for OAuth flows |
| Templates | Jinja2 | server-rendered HTML, no JS framework |
| HTTP client | httpx | async, used for OSM/Overpass/API requests |
| Auth | OSM OAuth 2.0 | PKCE flow, scopes: `read_prefs` + `write_api` |

---

## Project Structure

```
osmpoicms/
├── .python-version          # pyenv pin
├── .envrc                   # direnv: layout pyenv, dotenv .env
├── .env.example
├── pyproject.toml           # uv + ruff config
├── src/
│   └── osmpoicms/
│       ├── main.py          # FastAPI app, startup
│       ├── auth.py          # OSM OAuth 2.0 flow
│       ├── osm.py           # Overpass queries + OSM API writes
│       ├── models.py        # Pydantic models
│       ├── routes/
│       │   ├── index.py     # GET / — landing or dashboard
│       │   ├── auth.py      # /auth/login, /auth/callback, /auth/logout
│       │   └── pois.py      # /pois — query, edit, save
│       └── templates/
│           ├── base.html
│           ├── landing.html    # unauthenticated: only OSM connect button
│           ├── dashboard.html  # community picker + category selector
│           └── poi_table.html  # editable POI table + save flow
└── tests/
```

---

## Authentication — OSM OAuth 2.0

OSM supports OAuth 2.0 with PKCE (no client secret required for public clients).

**Flow:**
1. User clicks "Connect to my OpenStreetMap.org account"
2. App redirects to `https://www.openstreetmap.org/oauth2/authorize` with PKCE challenge
3. OSM redirects back to `/auth/callback?code=...`
4. App exchanges code for access token at `https://www.openstreetmap.org/oauth2/token`
5. App fetches user info from `https://api.openstreetmap.org/api/0.6/user/details.json`
6. Token + user info stored in a signed cookie (`itsdangerous`) with `max_age=90 days` — user stays logged in across browser restarts until they explicitly log out or revoke access on OSM

**Required OSM OAuth scopes:** `read_prefs write_api`
- `read_prefs` — read user profile
- `write_api` — create changesets and update node/way/relation tags

**Existing OSM app** (already registered on openstreetmap.org):
- Credentials stored in `.env` via `OSM_CLIENT_ID` / `OSM_CLIENT_SECRET` — never in code
- Token exchange uses HTTP Basic Auth `(CLIENT_ID, CLIENT_SECRET)`, not PKCE-only
- Add `http://localhost:8000/auth/callback` as additional Redirect URI in the OSM app settings

**App settings:** https://www.openstreetmap.org/oauth2/applications (already registered)
- Add Redirect URI: `http://localhost:8000/auth/callback` (dev), production URI configurable via env

---

## Views

### `/` — Landing (unauthenticated)

```
┌─────────────────────────────────┐
│                                 │
│                                 │
│   [ Connect to my               │
│     OpenStreetMap.org account ] │
│                                 │
│                                 │
└─────────────────────────────────┘
```

If session exists → redirect to `/dashboard`.

### `/dashboard` — Main view (authenticated)

```
┌──────────────────────────────────────────────┐
│  Community: [ Innsbruck              ▼ ]      │  ← typeahead, admin_level=8 AT
│  Category:  ( ) Restaurants                   │
│             ( ) Hotels                        │
│             ( ) Doctors                       │
│             ( ) Pharmacies                    │
│             ( ) Supermarkets                  │
│             ( ) Shopping                      │
│             ( ) Banks & ATMs                  │
│             ( ) Leisure                       │
│                                               │
│  [ Load POIs ]                                │
└──────────────────────────────────────────────┘
```

Category is a **single-select** (radio buttons). Community + category required before loading.

### POI table (appears below, or replaces dashboard section)

```
┌──────────────────────────────────────────────────────────────┐
│  Restaurants in Innsbruck — 47 results  (max 200)            │
│                                                              │
│  [ Save changes ]                                            │
├──────┬───────────────┬───────────┬──────────────┬───────────┤
│  OSM │ Name          │ Address   │ Phone        │ Website   │
├──────┼───────────────┼───────────┼──────────────┼───────────┤
│  🔗  │ [Gasthof Adl] │ [Main 1 ] │ [          ] │ [       ] │
│  🔗  │ [Zum Hirsch  ] │ [Berg 5 ] │ [+43 512..] │ [       ] │
│  ... │               │           │              │           │
├──────┴───────────────┴───────────┴──────────────┴───────────┤
│  [ Save changes ]                                            │
└──────────────────────────────────────────────────────────────┘
```

- All tag fields are `<input type="text">` — always editable
- Empty fields can be filled in → tag gets added to OSM element
- Existing fields can be overwritten → tag value gets updated
- Overwriting with empty string → tag gets **deleted** from OSM element
- OSM link (🔗) opens `https://www.openstreetmap.org/{type}/{id}` in new tab
- Result count shown; if exactly 200 a note: "Result limited to 200 — refine your selection"

---

## Save Flow

### Step 1 — User clicks "Save changes"

App computes a diff: original tags (from Overpass) vs. current form values.
Only POIs with at least one changed field are included.

Redirect / inline replace to a **confirmation screen**:

```
┌──────────────────────────────────────────────────────────────┐
│  Review your changes                                         │
│                                                              │
│  3 POIs will be updated:                                     │
│                                                              │
│  Gasthof Adler (node/123)                                    │
│    phone:  (empty) → +43 512 123456                          │
│    website: (empty) → https://gasthof-adler.at               │
│                                                              │
│  Zum Hirsch (node/456)                                       │
│    website: http://old.at → https://new.at                   │
│                                                              │
│  Café Berg (node/789)                                        │
│    opening_hours: deleted                                    │
│                                                              │
│  Comment:  [________________________________]  (required, max 255 chars) │
│  Source:   [________________________________]  (optional, max 255 chars) │
│                                                              │
│  [ ← Back to editing ]      [ Confirm & push to OSM ]       │
└──────────────────────────────────────────────────────────────┘
```

### Step 2 — User clicks "Confirm & push to OSM"

OSM API write sequence (using the user's OAuth token):

1. `PUT /api/0.6/changeset/create` — open changeset with comment + source tags
2. For each changed element:
   - `GET /api/0.6/{type}/{id}` — fetch current version (needed for version number)
   - `PUT /api/0.6/{type}/{id}` — upload full tag set with incremented version
3. `PUT /api/0.6/changeset/{id}/close` — close changeset

On success: show confirmation with changeset link (`https://www.openstreetmap.org/changeset/{id}`).
On partial failure: show which elements succeeded and which failed, keep changeset open until all done or explicitly closed.

---

## Community Search

Austrian municipalities = OSM `admin_level=8` + `boundary=administrative`.

**Lookup approach:** Nominatim structured search:
```
GET https://nominatim.openstreetmap.org/search
  ?country=at
  &q={user_input}
  &featuretype=settlement
  &format=jsonv2
  &limit=10
```

Result: OSM relation ID (e.g. `relation/123456`) used as the boundary for Overpass queries.

---

## POI Categories → OSM Tags

| Category | OSM tags queried |
|---|---|
| Restaurants | `amenity=restaurant`, `amenity=cafe`, `amenity=fast_food` |
| Hotels | `tourism=hotel`, `tourism=hostel`, `tourism=guest_house`, `tourism=motel` |
| Doctors | `amenity=doctors`, `amenity=clinic`, `healthcare=doctor` |
| Pharmacies | `amenity=pharmacy` |
| Supermarkets | `shop=supermarket`, `shop=convenience` |
| Shopping | `shop=clothes`, `shop=sports`, `shop=shoes`, `shop=electronics`, `shop=gift`, `shop=toys`, `shop=books`, `shop=department_store` |
| Banks & ATMs | `amenity=bank`, `amenity=atm` |
| Leisure | `leisure=park`, `leisure=swimming_pool`, `leisure=sports_centre`, `leisure=fitness_centre`, `leisure=tennis`, `leisure=playground`, `amenity=theatre`, `amenity=cinema` |

**Overpass query pattern (hard limit: 200):**
```
[out:json][timeout:30];
area(id:{area_id})->.searchArea;
(
  node[amenity=restaurant](area.searchArea);
  way[amenity=restaurant](area.searchArea);
  relation[amenity=restaurant](area.searchArea);
);
out center 200;
```

`out center 200` — Overpass hard limit at the query level, not post-filtered.
Note: OSM relation ID → Overpass area ID = relation ID + 3_600_000_000.

---

## Editable Tag Columns per Category

Shown as columns in the POI table. All other tags are preserved on write but not shown.

| Category | Columns shown |
|---|---|
| All | Name, Address (`addr:street` + `addr:housenumber`), Phone (`phone`), Website (`website`), Opening hours (`opening_hours`) |
| Restaurants | + Cuisine (`cuisine`) |
| Hotels | + Stars (`stars`), Rooms (`rooms`) |
| Doctors | + Specialty (`healthcare:speciality`) |
| Pharmacies | — |
| Supermarkets | — |
| Shopping | + Goods (`shop` value shown read-only) |
| Banks & ATMs | + Operator (`operator`) |
| Leisure | + Access (`access`) |

---

## OSM Write Logic — Tag Diff

Adapted from `osm_update.py`. Key difference: **empty string = delete tag** (the script skips empty values).

```python
def apply_updates(xml_str: str, new_tags: dict[str, str], changeset_id: str) -> tuple[str, list]:
    # new_tags: only the editable columns from the form
    # empty string value = delete that tag
    # key absent from new_tags = leave tag unchanged (not shown in UI)
    root = ET.fromstring(xml_str)
    element = root[0]
    element.set("changeset", changeset_id)

    existing = {t.get("k"): t for t in element.findall("tag")}
    changes = []

    # Remove legacy contact: tags if present
    for legacy in ("contact:email", "contact:phone", "contact:website", "url"):
        if legacy in existing:
            element.remove(existing.pop(legacy))
            changes.append(("DEL", legacy, existing[legacy].get("v"), None))

    for key, val in new_tags.items():
        if key in existing:
            old = existing[key].get("v")
            if val == "":           # empty → delete
                element.remove(existing[key])
                changes.append(("DEL", key, old, None))
            elif old != val:        # changed
                existing[key].set("v", val)
                changes.append(("UPD", key, old, val))
        elif val != "":             # new tag
            tag = ET.SubElement(element, "tag")
            tag.set("k", key)
            tag.set("v", val)
            changes.append(("ADD", key, None, val))

    xml_out = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_out}', changes
```

---

## Environment Variables

```
OSM_CLIENT_ID=           # from openstreetmap.org/oauth2/applications
OSM_CLIENT_SECRET=       # from openstreetmap.org/oauth2/applications
OSM_REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET=          # random 32-byte hex
```

---

## Build Steps

### Phase 1 — Skeleton
- [ ] Init repo: `uv init`, pyproject.toml, ruff config, .envrc, .python-version
- [ ] FastAPI app with session middleware (itsdangerous cookie)
- [ ] Landing page with OSM connect button
- [ ] OAuth 2.0 + PKCE flow (login, callback, logout) with scopes `read_prefs write_api`
- [ ] Session guard: redirect unauthenticated users to `/`

### Phase 2 — Community + category picker
- [ ] Nominatim typeahead endpoint (`GET /api/communities?q=...`)
- [ ] Dashboard template: community typeahead + single-select category radio buttons
- [ ] Store selected community (relation ID + display name) in session

### Phase 3 — POI table
- [ ] Overpass query builder per category with `out center 200` limit
- [ ] `GET /pois?community_id=...&category=...` endpoint
- [ ] Editable table: input fields pre-filled from OSM tags, empty where tag missing
- [ ] Save buttons above and below table; diff computed server-side from hidden original values

### Phase 4 — Confirmation + OSM write
- [ ] Confirmation screen: structured diff view (added / changed / deleted per POI)
- [ ] Comment (required, max 255 chars) + source (optional, max 255 chars) fields — validated client-side (`maxlength`) and server-side before changeset creation
- [ ] OSM API write: open changeset → update elements → close changeset
- [ ] Success screen with changeset link; error handling for version conflicts (refetch + retry once)

### Phase 5 — Polish
- [ ] Loading state during Overpass fetch
- [ ] "200 result limit reached" warning banner
- [ ] Basic styling (Bootstrap 5 or Pico CSS — no build step)
- [ ] Changeset link in success screen

---

## Gotchas

- **Version conflicts:** Between loading and saving, someone else may have edited the same element. Fetch current version just before each `PUT` and retry once on 409.
- **Ways and relations:** Overpass returns them with a `center` coordinate. OSM API `PUT` for ways/relations requires sending the full geometry (all node refs), not just tags — fetch the full element before writing.
- **Tag deletion:** OSM API does not have a "delete tag" operation. To delete a tag, simply omit it from the full tag set sent in the `PUT` request.
- **Overpass rate limits:** Public endpoint has rate limiting; large communities may hit it. Add a user-agent header with contact email.
