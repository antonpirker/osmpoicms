import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from osmpoicms.routes import api, auth, index


class LocalhostRedirect(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.hostname == "127.0.0.1":
            url = str(request.url).replace("127.0.0.1", "localhost", 1)
            return RedirectResponse(url, status_code=302)
        return await call_next(request)


app = FastAPI(title="OSM POI CMS")
app.add_middleware(LocalhostRedirect)
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(index.router)


def dev() -> None:
    uvicorn.run(
        "osmpoicms.main:app",
        reload=True,
        ssl_keyfile="localhost-key.pem",
        ssl_certfile="localhost.pem",
    )
