from datetime import datetime
from defrag.modules.helpers.sync_utils import as_async
from pydantic.main import BaseModel
from defrag import LOGGER
from defrag.modules.helpers.requests import Req
from defrag.modules.helpers.cache_stores import CacheStrategy, QStore, RedisCacheStrategy
from defrag.modules.helpers.services_manager import ServiceTemplate, ServicesManager
import atoma
from typing import Any, Dict, List
from operator import attrgetter

""" INFO
This module provides a class to query & store recent reddit posts (sent to "r/openSUSE"). 
Additional features could be:
- posting (would require higher credentials)
- fetching comments 
to model data answering the question: "What are people talking about recently?"
"""

__MOD_NAME__ = "reddit"


class RedditEntry(BaseModel):
    title: str
    url: str
    updated: float


class RedditStore(QStore):
    """
    Specialization of QStore to handle specifically data by this service / module.
    """

    @staticmethod
    async def fetch_items() -> List[RedditEntry]:
        """ Tries to fetch 25 most recent posts from r/openSUSE and extract title, url
        and update time in memory """
        async with Req("https://www.reddit.com/r/openSUSE/.rss") as response:
            try:
                if reddit_bytes := await response.read():
                    feed = atoma.parse_atom_bytes(reddit_bytes)
                    entries: List[RedditEntry] = [RedditEntry(
                        title=e.title.value, url=e.links[0].href, updated=datetime.timestamp(e.updated)) for e in feed.entries]
                    return sorted(entries, key=attrgetter("updated"))
                else:
                    raise Exception("Empty results from r/openSUSE")
            except Exception as err:
                await as_async(LOGGER.warn)("Unable to fetch r/openSUSE: ", err)
                return []

    def filter_fresh_items(self, items: List[RedditEntry]) -> List[Dict[str, Any]]:
        if not items or not self.container:
            return [i.dict() for i in items]
        return [i.dict() for i in items if getattr(i, "updated") > self.when_last_update]


async def search_reddit(keywords: str) -> List[RedditEntry]:

    async with Req(f"https://www.reddit.com/r/openSUSE/search.rss", params={"q": keywords, "sort": "relevance", "restrict_sr": 1, "type": "link", "limit": 75}) as response:
        if reddit_bytes := await response.read():
            feed = atoma.parse_atom_bytes(reddit_bytes)
            return [RedditEntry(title=e.title.value, url=e.links[0].href, updated=datetime.timestamp(e.updated)) for e in feed.entries]
        return []


def register_service():
    """ 
    The idea is that modules are registered against the
    service manager by calling this function. Can be called from @app.on_event('statupp'
    for example, or from somewhere else in __main__, or from RedditStore. To be discussed,
    but it's flexible enough to work with any decision.
    """
    name = "reddit"
    service_key = name + "_default"
    reddit_strategy = CacheStrategy(
        RedisCacheStrategy(populate_on_startup=True, auto_refresh=True, auto_refresh_delay=300, runner_timeout=None, cache_decay=None), None)
    reddit = ServiceTemplate(name=name, cache_strategy=reddit_strategy,
                             endpoint=None, port=None, credentials=None, custom_parameters=None)
    service = ServicesManager.realize_service_template(
        reddit, RedditStore(service_key))
    ServicesManager.register_service(name, service)
