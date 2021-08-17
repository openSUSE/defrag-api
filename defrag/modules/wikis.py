from pydantic.main import BaseModel
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.requests import Req
from defrag import app
from typing import List
from dateutil import parser

__MOD_NAME__ = "wikis"


class WikiEntry(BaseModel):
    wordcount: int
    timestamp: float
    title: str
    snippet: str


async def search_wikis(keywords: str) -> List[WikiEntry]:
    async with Req(f"https://en.opensuse.org/api.php", params={"action": "query", "list": "search", "srwhat": "text", "srsearch": keywords, "srlimit": 50, "format": "json"}) as response:
        if results_json := await response.json():
            return [WikiEntry(wordcount=i["wordcount"], timestamp=parser.isoparse(i["timestamp"]).timestamp(), title=i["title"], snippet=i["snippet"]) for i in results_json["query"]["search"]]
        return []


@app.get(f"/{__MOD_NAME__}/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search_wikis(keywords)
    query = Query(service=__MOD_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))
