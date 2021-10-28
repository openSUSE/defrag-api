from logging import error
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.cache_manager import memo_redis
from defrag.modules.search import SearchQuery, search_map
import asyncio

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "search"


@router.get("/" + __ENDPOINT_NAME__ + "/")
@memo_redis("/" + __ENDPOINT_NAME__ + "/")
async def global_search(keywords: str, scope: str) -> QueryResponse:
    query = Query(service="search")
    sq = SearchQuery(keywords=keywords, scope=[
                     s.strip() for s in scope.split(",")])
    off_scope = [s for s in sq.scope if not s in search_map.keys()]
    if off_scope:
        return QueryResponse(query=query, error=f"These scopes go beyond our current available scopes: {off_scope}")

    results = {}
    results_counts = 0
    for response in asyncio.as_completed([search(sq.keywords) for k, search in search_map.items() if k in sq.scope]):
        res = await response
        count = res.results_count
        results[res.query.service] = {
            "results": res.results, "results_count": count}
        results_counts += count
    return QueryResponse(query=query, results=results, results_count=results_counts)
