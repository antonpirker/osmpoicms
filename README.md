# OSM POI CMS

Web app for managing POI data for Austrian municipalities on OpenStreetMap.

---

## Setup

### 1. Create an OSM OAuth2 app

1. Log in to [openstreetmap.org](https://www.openstreetmap.org)
2. Go to **My Profile** (top right) → **My Settings** → **OAuth2 Applications**
3. Click **Register new application**
4. Fill in:
   - **Name:** anything, e.g. `OSM POI CMS`
   - **Redirect URIs:** `https://localhost:8000/auth/callback`
   - **Confidential application:** yes (check the box)
5. Under **Permissions**, check:
   - `Read user preferences`
   - `Modify the map`
6. Click **Register** and copy the **Client ID** and **Client Secret**

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```ini
OSM_CLIENT_ID=<your client id>
OSM_CLIENT_SECRET=<your client secret>
OSM_REDIRECT_URI=https://localhost:8000/auth/callback
SESSION_SECRET=<random string, generate with: openssl rand -hex 32>
```

### 3. Install dependencies

**Python dependencies** via [uv](https://docs.astral.sh/uv/):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

**mkcert** for local HTTPS (required by OSM OAuth2):

```bash
# Install mkcert
sudo apt install mkcert   # Debian/Ubuntu
brew install mkcert        # macOS

# Create local SSL certificate (run once)
mkcert -install
mkcert localhost
```

---

## Start the app

```bash
uv run dev
```

App runs at **https://localhost:8000**.
