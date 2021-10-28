from logging import error
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.cache_manager import Memo_Redis
from defrag.modules.search import SearchQuery, search_map
import asyncio

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "search"


@router.get("/" + __ENDPOINT_NAME__ + "/")
@Memo_Redis.install_decorator(f"/" + __ENDPOINT_NAME__ + "/")
async def global_search(keywords: str, scope: str) -> QueryResponse:
    query = Query(service="search")
    sq = SearchQuery(keywords=keywords, scope=[s.strip() for s in scope.split(",")])
    off_scope = [s for s in sq.scope if not s in search_map.keys()]
    if off_scope:
        return QueryResponse(query=query, error=f"These scopes go beyond our current available scopes: {off_scope}")
    
    results = {}
    results_counts = 0
    responses = await asyncio.gather(*[search(sq.keywords) for search in search_map.values()])
    
    for res in responses:
        count = res.results_count
        results[res.query.service] = {
            "results": res.results, "results_count": count}
        results_counts += count
    return QueryResponse(query=query, results=results, results_count=results_counts)
