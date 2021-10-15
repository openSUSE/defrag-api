import asyncio
from asyncio.tasks import Task
from pottery.deque import RedisDeque
import twitter
from typing import Any, Dict, List
from operator import attrgetter

from datetime import datetime
from pydantic.main import BaseModel
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from defrag import LOGGER, app, TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
from defrag.modules.helpers.cache_manager import Cache, Memo_Redis, Service
from defrag.modules.helpers.stores import BaseStore, ContainerCfg, Logs, StoreWorker, WorkerCfg
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.cache_manager import Run

""" INFO
This module provides a class to
serve as querying & storing point for recent tweets (sent by user "@openSUSE").
Additional features could be:
- posting (would require higher credentials)
- fetching also Tweets *about* openSUSE
to model data answering the question: "What are people talking about recently?"
"""

__MOD_NAME__ = "twitter"


api = twitter.Api(consumer_key=TWITTER_CONSUMER_KEY, consumer_secret=TWITTER_CONSUMER_SECRET,
                  access_token_key=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)


class TwitterEntry(BaseModel):
    contents: str
    created_at: str
    created_at_in_seconds: float
    id_str: str


class TwitterStore(StoreWorker, BaseStore):

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
        fetch = as_async(api.GetUserTimeline)
        entries = [TwitterEntry(contents=x.text, created_at_in_seconds=x.created_at_in_seconds, created_at=x.created_at, id_str=x.id_str) for x in await fetch(screen_name="@openSUSE")]
        sorted_entries = sorted(entries, key=attrgetter("created_at"))
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


async def search_tweets(keywords: str) -> List[TwitterEntry]:
    try:
        search = as_async(api.GetSearch)
        raw_query = f"q=openSUSE {keywords}&result_type=recent&count=100"
        results = await search(raw_query=raw_query)
        return [TwitterEntry(contents=x.text, created_at_in_seconds=x.created_at_in_seconds, created_at=x.created_at, id_str=x.id_str) for x in results]
    except Exception as err:
        await as_async(LOGGER.warning)("Unable to fetch from Twitter @opensuse: ", err)
        return []


def register_service():
    name = "twitter"
    service_key = name + "_default"
    service_key = __MOD_NAME__ + "_default"
    worker_config = WorkerCfg(
        True, "https://www.reddit.com/r/openSUSE.rss", 900, 30)
    container_config = ContainerCfg(service_key)
    twitter_store = TwitterStore(container_config, worker_config)
    service = Service(datetime.now(), store=twitter_store)
    Cache.register_service(__MOD_NAME__, service)


@app.get(f"/{__MOD_NAME__}/search/")
@Memo_Redis.install_decorator("/" + __MOD_NAME__ + "/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search_tweets(keywords)
    query = Query(service=__MOD_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))


@app.get(f"/{__MOD_NAME__}/")
async def get_twitter() -> QueryResponse:
    query = CacheQuery(service=__MOD_NAME__)
    async with Run(query) as response:
        return response
