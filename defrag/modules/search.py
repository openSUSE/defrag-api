from importlib import import_module
from defrag.modules import ALL_MODULES
from defrag.modules.helpers import Query, QueryResponse
from typing import List
from pydantic import BaseModel
from defrag import app
from defrag.modules.helpers.services_manager import ServicesManager
import asyncio

__MOD_NAME__ = "global_search"

search_map = {f: getattr(m, "search") for f, m in [(n, import_module(
    f"defrag.modules.{n}")) for n in ALL_MODULES] if hasattr(m, "search")}


class SearchQuery(BaseModel):
    keywords: str
    scope: List[str]


@app.get(f"/{__MOD_NAME__}/")
async def global_search(keywords: str, scope: str) -> QueryResponse:
    query = Query(service=__MOD_NAME__)
    sq = SearchQuery(keywords=keywords, scope=[s.strip() for s in scope.split(",")])
    """
    TODO: the idea of making registered services a precondition for searching globally
    was that we would be using some cache. Not the case for now so dropping this precondition
    until we have a more intelligent solution.
    
    if missing_services := [s for s in sq.scope if not s in ServicesManager.services.list_enabled()]:
        error = f"You are trying to search from services that have not been enabled yet: {missing_services}"
        return QueryResponse(query=query, error=error)
    """
    searchers = [f for n, f in search_map.items() if n in sq.scope]
    results = {}
    results_counts = 0
    for response in asyncio.as_completed([search(sq.keywords) for search in searchers]):
        res = await response
        count = res.results_count
        results[res.query.service] = {
            "results": res.results, "results_count": count}
        results_counts += count
    return QueryResponse(query=query, results=results, results_count=results_counts)
