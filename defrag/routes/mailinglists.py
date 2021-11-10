from fastapi import APIRouter

from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.mailinglists import MailingLists

router = APIRouter()

__ENDPOINT_NAME__ = "mailinglists"


@router.get("/" + __ENDPOINT_NAME__ + "/")
async def get_feeds(list_names: str) -> QueryResponse:
    query = Query(service=__ENDPOINT_NAME__)
    try:
        _list_names = list_names.lower().split(",")
        res = await MailingLists.get_feeds(*_list_names)
        return QueryResponse(query=query, results=res, results_count=len(res))
    except Exception as error:
        return QueryResponse(query=query, error=error, message="Request failed. Check error message.")


@router.get("/" + __ENDPOINT_NAME__ + "/search/")
async def search_feeds(keywords: str) -> QueryResponse:
    query = Query(service=__ENDPOINT_NAME__)
    try:
        _keywords = keywords.lower().split(",")
        res = MailingLists.search_idx(*_keywords)
        return QueryResponse(query=query, results=res, results_count=len(res))
    except Exception as error:
        return QueryResponse(query=query, error=error, message="Request failed. Check error message.")

    