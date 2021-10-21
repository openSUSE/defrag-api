from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.helpers.cache_manager import Memo_Redis, Run, CacheQuery
from defrag.modules.twitter import search_tweets

from fastapi import APIRouter
router = APIRouter()


__ENDPOINT_NAME__ = "twitter"

@router.get(f"/{__ENDPOINT_NAME__}/search/")
@Memo_Redis.install_decorator("/" + __ENDPOINT_NAME__ + "/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search_tweets(keywords)
    query = Query(service=__ENDPOINT_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))


@router.get(f"/{__ENDPOINT_NAME__}/")
async def get_twitter() -> QueryResponse:
    query = CacheQuery(service=__ENDPOINT_NAME__)
    async with Run(query) as response:
        return response
