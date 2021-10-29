from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.cache import Memo
from defrag.modules.bugs import get_this_bug, search

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "bug"
query = Query(service=__ENDPOINT_NAME__)

@router.get("/" + __ENDPOINT_NAME__ + "/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[
                         {"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])


@router.get("/" + __ENDPOINT_NAME__ + "/bug/{bug_id}")
@Memo(**{"memo_key":"/" + __ENDPOINT_NAME__ + "/bug/"})
async def get_bug(bug_id: int) -> QueryResponse:
    query.args = bug_id
    query.function = "get_bug"
    res = list(await get_this_bug(bug_id))
    return QueryResponse(query=query, results=res, results_count=len(res))


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@Memo(**{"memo_key":"/" + __ENDPOINT_NAME__ + "/search/"})
async def search(term: str) -> QueryResponse:
    return await search(term)