import asyncio
from asyncio.tasks import Task
from datetime import datetime
from pottery.deque import RedisDeque
from typing import Any, Dict, List
from operator import attrgetter
import atoma

from defrag import app
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.cache_manager import Cache, Run, Service, memo_redis
from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from pydantic.main import BaseModel
from defrag.modules.helpers.requests import Req
from defrag.modules.helpers.stores import ContainerCfg, Logs, StoreWorker, BaseStore, WorkerCfg

""" INFO
This module provides a class to query & store recent reddit posts (sent to "r/openSUSE"). 
Additional features could be:
- posting (would require higher credentials)
- fetching comments 
to model data answering the question: "What are people talking about recently?"
"""

__MOD_NAME__ = "reddit"


class RedditStore(StoreWorker, BaseStore):

    class RedditEntry(BaseModel):
        title: str
        url: str
        updated: float

    def __init__(self, container_config: ContainerCfg, worker_config: WorkerCfg) -> None:
        self.container: RedisDeque = RedisDeque(
            key=container_config.redis_key, redis=RedisPool().connection)
        self.id_key = container_config.id_key
        self.updated_key = container_config.updated_key
        self.logs = Logs()
        self.worker_config = worker_config

    def to_keep(self, items: List[Any]) -> List[Any]:
        if not items or not self.container:
            return [i.dict() for i in items]
        return [i.dict() for i in items if getattr(i, self.updated_key) > self.logs.last_refresh]

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
            raise Exception("Tried to refresh RedditStore, but no worker_config.fetch_endpoint set.")
        async with Req(self.worker_config.worker_fetch_endpoint) as response:
            reddit_bytes = await response.read()
            feed = atoma.parse_atom_bytes(reddit_bytes)
            entries = [
                RedditStore.RedditEntry(
                    title=e.title.value,
                    url=e.links[0].href,
                    updated=datetime.timestamp(e.updated)
                )
                for e in feed.entries
            ]
            sorted_entries = sorted(entries, key=attrgetter(self.updated_key))
            self.update_with([e.dict() for e in sorted_entries])
            self.logs.last_refresh = datetime.now().timestamp()

    def evict(self) -> None:
        pass

    def create_worker(self) -> Task:
        async def run():
            if not self.worker_config.worker_interval:
                raise Exception(
                    "Tried to create a worker from RedditStore, but no worker_config.worker interval set.")
            await asyncio.sleep(self.worker_config.worker_interval)
            try:
                await asyncio.wait_for(self.refresh(), timeout=self.worker_config.worker_timeout)
                self.logs.last_worker_run = datetime.now().timestamp()
            except asyncio.exceptions.TimeoutError:
                self.log_with(
                    {"msg": f"timedout after {self.worker_config.worker_timeout} seconds."})
            finally:
                await run()
        return asyncio.create_task(run())


async def search_reddit(keywords: str) -> List[RedditStore.RedditEntry]:

    async with Req("https://www.reddit.com/r/openSUSE/search.rss", params={"q": keywords, "sort": "relevance", "restrict_sr": 1, "type": "link", "limit": 75}) as response:
        if reddit_bytes := await response.read():
            feed = atoma.parse_atom_bytes(reddit_bytes)
            return [RedditStore.RedditEntry(title=e.title.value, url=e.links[0].href, updated=datetime.timestamp(e.updated)) for e in feed.entries]
        return []


def register_service():
    """ 
    The idea is that modules are registered against the
    service manager by calling this function. Can be called from @app.on_event('statupp'
    for example, or from somewhere else in __main__, or from RedditStore. To be discussed,
    but it's flexible enough to work with any decision.
    """
    service_key = __MOD_NAME__ + "_default"
    worker_config = WorkerCfg(
        True, "https://www.reddit.com/r/openSUSE.rss", 900, 30)
    container_config = ContainerCfg(service_key)
    reddit_store = RedditStore(container_config, worker_config)
    service = Service(datetime.now(), store=reddit_store)
    Cache.register_service(__MOD_NAME__, service)


@app.get("/" + __MOD_NAME__ + "/search/")
#@memo_redis("/" + __MOD_NAME__ + "/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search_reddit(keywords)
    query = Query(service=__MOD_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))


@app.get(f"/{__MOD_NAME__}/")
async def get_reddit() -> QueryResponse:
    query = CacheQuery(service=__MOD_NAME__)
    async with Run(query) as response:
        return response
