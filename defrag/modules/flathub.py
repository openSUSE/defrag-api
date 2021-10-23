from lunr import lunr
from lunr.index import Index

from typing import List, Optional
from pydantic.main import BaseModel
from defrag.modules.helpers.requests import Session

__MOD_NAME__ = "flathub"

base_url = "https://flathub.org/api/v1/apps"
categories = [
    "AudioVideo",
    "Development",
    "Education",
    "Game",
    "Graphics",
    "Network",
    "Office",
    "Science",
    "System",
    "Utility"
]
index = None


class FlatHubEntry(BaseModel):
    flatpakAppId: str
    name: str
    summary: str
    currentReleaseVersion: Optional[str]
    currentReleaseDate: str
    iconDesktopUrl: Optional[str]
    iconMobileUrl: Optional[str]
    inStoreSinceDate: Optional[str]


def make_index(items: List[FlatHubEntry]) -> Index:
    documents = [i.dict() for i in items]
    return lunr(ref="flatpakAppId", fields=("name", "summary"), documents=documents)


async def list_apps(category: Optional[str] = None) -> List[FlatHubEntry]:
    url = f"{base_url}/category/{category}" if category in categories else base_url
    response = await Session().get(url)
    res = await response.json()
    return [FlatHubEntry(**v) for v in res] if res else []


async def search(keywords: str) -> List[str]:
    global index
    if not index:
        index = make_index(await list_apps())
    return [item["ref"] for item in index.search(keywords)]