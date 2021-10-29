from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.helpers.cache import Memo
from defrag.modules.wikis import search

from fastapi import APIRouter
router = APIRouter()


__ENDPOINT_NAME__ = "wikis"


@router.get("/" +  __ENDPOINT_NAME__ + "/search/")
@Memo(**{"memo_key":"/" + __ENDPOINT_NAME__ + "/search/"})
async def search_wikis(keywords: str) -> QueryResponse:
    results = await search(keywords)
    query = Query(service="wikis")
    return QueryResponse(query=query, results=results, results_count=len(results))
