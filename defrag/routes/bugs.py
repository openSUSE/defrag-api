from functools import partial
from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from defrag.modules.helpers.services_manager import Run
from defrag.modules.bugs import get_this_bug, BugzillaQueryEntry, search_all_bugs

from fastapi import APIRouter
router = APIRouter()

""" Bugs """


@router.get("/bug/{bug_id}")
async def get_bug(bug_id: int) -> QueryResponse:
    # declares how this request should interface with the cache
    cache_query = CacheQuery(service="bugs", item_key=bug_id)
    # declares what function to run if the item the request is looking for
    # cannot find it in the cache store
    fallback = partial(get_this_bug, bug_id)
    # run the request
    return await Run.query(cache_query, fallback)


@router.get("/bugs/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[
                         {"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])


@router.get("/bugs/search/")
async def search(term: str) -> QueryResponse:
    query = BugzillaQueryEntry(search_string=term)
    result = await search_all_bugs(query)
    # This is not as fancy as it was before, but now it actually works.
    # Plus, before id didn't cache anyway, so this should be fine. We can
    # still make it better in the future
    return QueryResponse(
        query=Query(
            service="bugs"),
        results_count=len(result),
        results=result)
