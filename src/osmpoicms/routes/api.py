from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from osmpoicms.osm import search_communities

router = APIRouter(prefix="/api")


@router.get("/communities")
async def communities(q: str = Query(min_length=2)):
    results = await search_communities(q)
    return JSONResponse(results)
