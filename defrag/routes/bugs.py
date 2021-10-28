from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from defrag.modules.helpers.cache_manager import memo_redis, Run
from defrag.modules.bugs import BugzillaQueryEntry, search

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "bug"


@router.get("/" + __ENDPOINT_NAME__ + "/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[
                         {"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])


@router.get("/" + __ENDPOINT_NAME__ + "/bug/{bug_id}")
@memo_redis("/" + __ENDPOINT_NAME__ + "/bug/")
async def get_bug(bug_id: int) -> QueryResponse:
    query = CacheQuery(service="bugs", item_id=bug_id)
    async with Run(query) as response:
        return response


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@memo_redis("/" + __ENDPOINT_NAME__ + "/search/")
async def search(term: str) -> QueryResponse:
    result = await search(BugzillaQueryEntry(search_string=term))
    return QueryResponse(query=Query(service="bugs"), results_count=len(result), results=result)
