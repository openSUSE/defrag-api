from defrag.modules.helpers import QueryResponse
from defrag.modules.helpers.cache_manager import Memo_Redis
from defrag.modules.api import search

from fastapi import APIRouter
router = APIRouter()

__ENDPOINT_NAME__ = "api"

@router.get("/" + __ENDPOINT_NAME__ + "/search/{distribution}")
@Memo_Redis.install_decorator("/" + __ENDPOINT_NAME__ + "/search/")
async def api_search(keywords: str, distribution: str) -> QueryResponse:
    res = await search(keywords, distribution)
    return QueryResponse(results=res, results_count=len(res))
