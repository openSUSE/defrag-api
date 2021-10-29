from pydantic.main import BaseModel
from defrag.modules.helpers.requests import Session
from typing import List
from dateutil import parser

__MOD_NAME__ = "wikis"


class WikiGenEntry(BaseModel):
    page_id: int
    title: str
    index: int


class WikiListEntry(BaseModel):
    wordcount: int
    timestamp: float
    title: str
    snippet: str
    url: str


def title_to_url(title: str, base_url="https://en.opensuse.org/") -> str:
    return base_url + title.replace(" ", "_")


async def search(keywords: str) -> List[WikiListEntry]:
    try:
        response = await Session().get("https://en.opensuse.org/api.php", params={"action": "query", "list": "search", "srwhat": "text", "srsearch": keywords, "srnamespace": "0|2|4|6|10|12|14|100|102|104|106", "srlimit": 50, "format": "json"})
        if results_json := await response.json():
            return [WikiListEntry(url=title_to_url(i["title"]), wordcount=i["wordcount"], timestamp=parser.isoparse(i["timestamp"]).timestamp(), title=i["title"], snippet=i["snippet"]) for i in results_json["query"]["search"]]
        return []
    except Exception as error:
        print(f"Found this error while searching the wikis, {error}")
        return []
