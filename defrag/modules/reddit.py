import asyncio
from asyncio.tasks import Task
from datetime import datetime
from dateutil.parser.isoparser import isoparse
from pottery.deque import RedisDeque
from typing import Any, Dict, List
from operator import attrgetter
import feedparser

from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.cache_manager import Cache, Service
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

    def __init__(self, container_config: ContainerCfg, worker_config: WorkerCfg) -> None:
        self.container: RedisDeque = RedisDeque(
            key=container_config.redis_key, redis=RedisPool().connection)
        self.id_key = container_config.id_key
        self.updated_key = container_config.updated_key
        self.logs = Logs()
        self.worker_config = worker_config
        if worker_config.worker:
            self.worker = asyncio.create_task(self.create_worker())

    def to_keep(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def fresher(its): return (
            i for i in its if i[self.updated_key] > self.logs.last_refresh)
        if not items or not self.container or not any(fresher(items)):
            return items
        return list(fresher(items))

    def to_evict(self) -> List[Any]:
        return []

    def update_with(self, items: List[Dict[str, Any]]) -> None:
        self.container.extendleft(self.to_keep(items))

    async def fallback(self, cache_query: CacheQuery) -> List[Dict[str, Any]]:
        await self.refresh()
        return self.evaluate(cache_query)

    async def warmup(self) -> None:
        await self.refresh()

    async def refresh(self) -> None:
        if not self.worker_config.worker_fetch_endpoint:
            raise Exception(
                "Tried to refresh RedditStore, but no worker_config.fetch_endpoint set.")
        entries = await parser(self.worker_config.worker_fetch_endpoint)
        sorted_entries = sorted(entries, key=attrgetter(self.updated_key))
        self.update_with([e.dict() for e in sorted_entries])
        self.logs.last_refresh = datetime.now().timestamp()


async def search_reddit(keywords: str) -> List[RedditPostEntry]:
    return await parser(f"https://www.reddit.com/r/openSUSE/search.rss?q={keywords}&sort=relevance&restrict_sr=1&type=link&limit=75")


def register_service():
    service_key = __MOD_NAME__ + "_default"
    worker_config = WorkerCfg(
        True, "https://www.reddit.com/r/openSUSE.rss", 900, 30)
    container_config = ContainerCfg(service_key)
    reddit_store = RedditStore(container_config, worker_config)
    service = Service(datetime.now(), store=reddit_store)
    Cache.register_service(__MOD_NAME__, service)
