from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.helpers.cache_manager import memo_redis, Run, CacheQuery
from defrag.modules.twitter import search

from fastapi import APIRouter
router = APIRouter()


__ENDPOINT_NAME__ = "twitter"

@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@memo_redis(f"/" + __ENDPOINT_NAME__ + "/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search(keywords)
    query = Query(service=__ENDPOINT_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))


@router.get("/" + __ENDPOINT_NAME__ + "/")
async def get_twitter() -> QueryResponse:
    query = CacheQuery(service=__ENDPOINT_NAME__)
    async with Run(query) as response:
        return response
