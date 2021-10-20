from functools import partial
from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from defrag.modules.helpers.cache_manager import Memo_Redis, Run
from defrag.modules.bugs import get_this_bug, BugzillaQueryEntry, search_all_bugs

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "bug"


@router.get("/" + __ENDPOINT_NAME__ + "/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[
                         {"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])


@router.get("/" + __ENDPOINT_NAME__ + "/bug/{bug_id}")
@Memo_Redis.install_decorator("/" + __ENDPOINT_NAME__ + "/bug/")
async def get_bug(bug_id: int) -> QueryResponse:
    query = CacheQuery(service="bugs", item_id=bug_id)
    async with Run(query) as response:
        return response


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@Memo_Redis.install_decorator("/" + __ENDPOINT_NAME__ + "/search/")
async def search(term: str) -> QueryResponse:
    query = BugzillaQueryEntry(search_string=term)
    result = await search_all_bugs(query)
    return QueryResponse(query=Query(service="bugs"), results_count=len(result), results=result)
