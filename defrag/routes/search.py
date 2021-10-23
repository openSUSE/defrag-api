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
    searchers = [f for n, f in search_map.items() if n in sq.scope]
    results = {}
    results_counts = 0
    for response in asyncio.as_completed([search(sq.keywords) for search in searchers]):
        res = await response
        count = res.results_count
        results[res.query.service] = {
            "results": res.results, "results_count": count}
        results_counts += count
    return QueryResponse(query=query, results=results, results_count=results_counts)
