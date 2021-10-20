from defrag.modules.helpers import QueryResponse, Query, CacheQuery
from defrag.modules.helpers.services_manager import Run
from defrag.modules.reddit import search_reddit

from fastapi import APIRouter
router = APIRouter()

""" Reddit """


@router.get("/reddit/search/")
async def handle_search_reddit(keywords: str) -> QueryResponse:
    results = await search_reddit(keywords)
    query = Query(service="reddit")
    return QueryResponse(query=query, results=results, results_count=len(results))


@router.get("/reddit/")
async def get_reddit() -> QueryResponse:
    query = CacheQuery(service="reddit", item_key=None)
    return await Run.query(query, None)
