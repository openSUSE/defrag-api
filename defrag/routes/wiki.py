from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.helpers.cache_manager import Memo_Redis
from defrag.modules.wikis import search_wikis_as_list

from fastapi import APIRouter
router = APIRouter()


__ENDPOINT_NAME__ = "wiki"


@router.get("/{__ENDPOINT_NAME__}/search/")
@Memo_Redis.install_decorator(f"/{__ENDPOINT_NAME__}/search/")
async def handle_search_wikis(keywords: str) -> QueryResponse:
    results = await search_wikis_as_list(keywords)
    query = Query(service="wiki")
    return QueryResponse(query=query, results=results, results_count=len(results))
