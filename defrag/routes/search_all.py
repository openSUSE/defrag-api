import asyncio
from fastapi import APIRouter


from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.cache import Memo
from defrag.modules.search_all import SearchQuery, search_map
router = APIRouter()

__ENDPOINT_NAME__ = "search"


@router.get("/" + __ENDPOINT_NAME__ + "/")
@Memo(**{"memo_key":"/" + __ENDPOINT_NAME__ + "/"})
async def search_all(keywords: str, scope: str) -> QueryResponse:
    query = Query(service="search")
    sq = SearchQuery(keywords=keywords, scope=[
                     s.strip() for s in scope.split(",")])
    off_scope = [s for s in sq.scope if not s in search_map.keys()]
    if off_scope:
        return QueryResponse(query=query, error=f"These scopes go beyond our current available scopes: {off_scope}")

    total_res = []
    total_res_count = 0
    for response in asyncio.as_completed([search(sq.keywords) for k, search in search_map.items() if k in sq.scope]):
        res = await response
        count = len(res)
        total_res.append({
            "results": res,
            "results_count": count
        })
        total_res_count += count
    return QueryResponse(query=query, results=total_res, results_count=total_res_count)
