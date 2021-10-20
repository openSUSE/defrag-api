from defrag.modules.helpers import QueryResponse, Query, CacheQuery
from defrag.modules.helpers.services_manager import Run
from defrag.modules.twitter import search_tweets

from fastapi import APIRouter
router = APIRouter()


""" Twitter """


@router.get("/twitter/")
async def handle_get_twitter() -> QueryResponse:
    return await Run.query(CacheQuery(service="twitter", item_key="id_str"))


@router.get("twitter/search/")
async def handle_search_tweets(keywords: str) -> QueryResponse:
    results = await search_tweets(keywords)
    query = Query(service="twitter")
    return QueryResponse(query=query, results=results, results_count=len(results))
