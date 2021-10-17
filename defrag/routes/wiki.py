from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.wikis import search_wikis_as_list

from fastapi import APIRouter
router = APIRouter()

""" Wikis """


@router.get("/wiki/search/")
async def handle_search_wikis(keywords: str) -> QueryResponse:
    results = await search_wikis_as_list(keywords)
    query = Query(service="wiki")
    return QueryResponse(query=query, results=results, results_count=len(results))
