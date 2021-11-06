from datetime import datetime
from dateutil.parser.isoparser import isoparse
from pottery.deque import RedisDeque
from typing import Any, Dict, List
from operator import attrgetter
import feedparser

from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import CacheQuery
from pydantic.main import BaseModel
from defrag.modules.helpers.stores import ContainerCfg, Logs, StoreWorkerMixin, BaseStore, WorkerCfg
from defrag.modules.helpers.sync_utils import as_async

""" INFO
This module provides a class to query & store recent reddit posts (sent to "r/openSUSE"). 
Additional features could be:
- posting (would require higher credentials)
- fetching comments 
to model data answering the question: "What are people talking about recently?"
"""

__MOD_NAME__ = "reddit"


class RedditPostEntry(BaseModel):
    title: str
    summary: str
    published: str
    updated: float
    link: str


async def parser(ressource_url: str) -> List[RedditPostEntry]:
    feed = await as_async(feedparser.parse)(ressource_url)
    parsed = [RedditPostEntry(
        title=e.title,
        summary=e.summary,
        published=e.published,
        updated=isoparse(e.updated).timestamp(),
        link=e.link
    )
        for e in feed.entries
    ]
    return parsed


class RedditStore(StoreWorkerMixin, BaseStore):

    def __init__(self, container_config: ContainerCfg, worker_cfg: WorkerCfg) -> None:
        self.container: RedisDeque = RedisDeque(
            key=container_config.redis_key, redis=RedisPool().connection)
        self.container_config = container_config
        self.worker_cfg = worker_cfg
        self.updated_key = container_config.updated_key
        self.logs = Logs()

    def to_keep(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def fresher(its): return (
            i for i in its if i[self.updated_key] > self.logs.last_refresh)
        if not items or not self.container or not any(fresher(items)):
            return items
        return list(fresher(items))

    async def update_with(self, items: List[Dict[str, Any]]) -> None:
        self.container.extendleft(self.to_keep(items))

    async def fallback(self, cache_query: CacheQuery) -> List[Dict[str, Any]]:
        await self.refresh()
        return self.evaluate(cache_query)

    async def warmup(self) -> None:
        await self.refresh()

    async def refresh(self) -> None:
        if not self.worker_cfg.worker_fetch_endpoint:
            raise Exception(
                "Tried to refresh RedditStore, but no worker_cfg.fetch_endpoint set.")
        entries = await parser(self.worker_cfg.worker_fetch_endpoint)
        sorted_entries = sorted(entries, key=attrgetter(self.updated_key))
        await self.update_with([e.dict() for e in sorted_entries])
        self.logs.last_refresh = datetime.now().timestamp()


async def search(keywords: str) -> List[RedditPostEntry]:
    return await parser(f"https://www.reddit.com/r/openSUSE/search.rss?q={keywords}&sort=relevance&restrict_sr=1&type=link&limit=75")


def make_store() -> RedditStore:
    service_key = __MOD_NAME__ + "_default"
    worker_cfg = WorkerCfg(
        True, "https://www.reddit.com/r/openSUSE.rss", 900, 30)
    container_config = ContainerCfg(service_key)
    return RedditStore(container_config, worker_cfg)