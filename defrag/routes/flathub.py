from typing import Optional
from fastapi import APIRouter
from defrag.modules.flathub import list_apps, search
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.cache_manager import Memo_Redis
import asyncio

router = APIRouter()

__ENDPOINT_NAME__ = "flathub"


@router.get("/" + __ENDPOINT_NAME__ + "/apps")
@Memo_Redis.install_decorator(__ENDPOINT_NAME__ + "/apps/")
async def get_apps(category: Optional[str] = None) -> QueryResponse:
    query = Query(service=__ENDPOINT_NAME__)
    results = await list_apps(category)
    return QueryResponse(query=query, results=results, results_count=len(results))


@router.get(f"/{__ENDPOINT_NAME__}/apps/search")
@Memo_Redis.install_decorator(__ENDPOINT_NAME__ + "/apps/search")
async def search_apps(keywords: str) -> QueryResponse:
    query = Query(service=__ENDPOINT_NAME__)
    found, apps = await asyncio.gather(search(keywords), get_apps())
    results = [e for e in apps.results if e.flatpakAppId in found]
    return QueryResponse(query=query, results=results, results_count=len(results))
