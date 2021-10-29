from fastapi import APIRouter


from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.helpers.cache import Stores, Memo, CacheQuery
from defrag.modules.twitter import make_store, search

router = APIRouter()

__ENDPOINT_NAME__ = "twitter"


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
@Memo(**{"memo_key":"/" + __ENDPOINT_NAME__ + "/search/"})
async def search_twitter(keywords: str) -> QueryResponse:
    res = await search(keywords)
    return QueryResponse(query=Query(service="twitter"), results=res, results_count=len(res))


@router.get("/" + __ENDPOINT_NAME__ + "/")
@Stores(**{"store_key": __ENDPOINT_NAME__, "builder": make_store})
async def get_twitter() -> QueryResponse:
    res = await Stores.run(query=CacheQuery(service=__ENDPOINT_NAME__))
    return QueryResponse(query=Query(service="twitter"), results=res, results_count=len(res))
