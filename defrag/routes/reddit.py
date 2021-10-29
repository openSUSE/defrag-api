from defrag.modules.helpers import QueryResponse, Query, CacheQuery
from defrag.modules.helpers.cache import Memo, Stores
from defrag.modules.reddit import search, make_store

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "reddit"


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@Memo(**{"memo_key":"/" + __ENDPOINT_NAME__ + "/search"})
async def search_reddit(keywords: str) -> QueryResponse:
    res = await search(keywords)
    return QueryResponse(query=Query(service=__ENDPOINT_NAME__), results=res, results_count=len(res))


@router.get("/" + __ENDPOINT_NAME__ + "/")
@Stores(**{"store_key": __ENDPOINT_NAME__, "builder": make_store})
async def get_reddit() -> QueryResponse:
    res = await Stores.run(query=CacheQuery(service=__ENDPOINT_NAME__))
    return QueryResponse(query=Query(service=__ENDPOINT_NAME__), results=res, results_count=len(res))
