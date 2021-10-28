from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.docs import *

from fastapi import APIRouter

from defrag.modules.helpers.cache_manager import memo_redis
router = APIRouter()


__ENDPOINT_NAME__ = "docs"


@router.get("/" + __ENDPOINT_NAME__ + "/search/single/{source}")
@memo_redis(f"/" + __ENDPOINT_NAME__ + "/search/single/")
async def search_single_source_docs(source: str, keywords: str) -> QueryResponse:
    if not ready_to_index([source]):
        await set_indexes()
    results = sorted_on_score(search_index(
        indexes[source]["index"], source, keywords))
    return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)


@router.get("/" + __ENDPOINT_NAME__ + "/search/merged/")
@memo_redis(f"/" + __ENDPOINT_NAME__ + "/search/merged/")
async def handle_search_docs(keywords: str) -> QueryResponse:
    if not ready_to_index(["leap", "tumbleweed"]):
        await set_indexes()
    results = sorted_on_score(search(keywords))
    return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)
