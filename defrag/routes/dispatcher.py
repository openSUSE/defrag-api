from typing import Optional
from fastapi import APIRouter


from defrag.modules.helpers.dispatcher import Dispatcher
from defrag.modules.helpers import Query, QueryResponse

router = APIRouter()


__ENDPOINT_NAME__ = "dispatcher"


@router.get("/" + __ENDPOINT_NAME__ + "/poll_due/")
async def poll_due(sync: Optional[bool] = None) -> QueryResponse:
    query = Query(service="dispatcher")
    results = await Dispatcher.poll_due(True if sync is None else sync)
    return QueryResponse(query=query, results_count=len(results), results=results)
