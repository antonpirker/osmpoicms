import uvicorn
from fastapi import FastAPI

from osmpoicms.routes import auth, index

app = FastAPI(title="OSM POI CMS")
app.include_router(auth.router)
app.include_router(index.router)


def dev() -> None:
    uvicorn.run(
        "osmpoicms.main:app",
        reload=True,
        ssl_keyfile="localhost-key.pem",
        ssl_certfile="localhost.pem",
    )
