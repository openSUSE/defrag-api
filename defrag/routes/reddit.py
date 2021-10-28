from defrag.modules.helpers import QueryResponse, Query, CacheQuery
from defrag.modules.helpers.cache_manager import Memo_Redis, Run
from defrag.modules.reddit import search

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "reddit"


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@Memo_Redis.install_decorator("/" + __ENDPOINT_NAME__ + "/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search(keywords)
    query = Query(service=__ENDPOINT_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))


@router.get("/" + __ENDPOINT_NAME__ + "/")
async def get_reddit() -> QueryResponse:
    query = CacheQuery(service=__ENDPOINT_NAME__)
    async with Run(query) as response:
        return response
