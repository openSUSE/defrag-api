from typing import Optional
from fastapi import APIRouter
from defrag.modules.suggestions import Suggestions

from defrag.modules.helpers import Query, QueryResponse
router = APIRouter()


""" Suggestions """


@router.get("/suggestions/")
async def get_suggestions(key: Optional[str] = None) -> QueryResponse:
    query = Query(service="suggestions")
    results = await Suggestions.view(key)
    if ok := results.is_ok():
        return QueryResponse(query=query, results=results, results_count=len(ok))
    return QueryResponse(query=query, error=str(ok))


@router.post("/suggestions/create/")
async def create_suggestion(sugg: Suggestions.New) -> QueryResponse:
    query = Query(service="suggestions")
    result = await Suggestions.add(sugg)
    if result.is_ok():
        return QueryResponse(query=query, message="Thanks!")
    return QueryResponse(query=query, error="Didn't turn out the way we anticipated!")


@router.post("/suggestions/vote_for_suggestion/")
async def vote_for_suggestion(voter_id: str, sugg_id: str, vote: int) -> QueryResponse:
    query = Query(service="suggestions")
    result = await Suggestions.cast_vote(voter_id=voter_id, key=sugg_id, vote=vote)
    if result.is_ok():
        return QueryResponse(query=query, message="Thanks!")
    return QueryResponse(query=query, error=result.error)

