from datetime import datetime
from pydantic.main import BaseModel
from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from defrag import LOGGER, app, TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
from defrag.modules.helpers.cache_stores import CacheStrategy, QStore, RedisCacheStrategy
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.services_manager import Run, ServiceTemplate, ServicesManager
import twitter
from typing import Any, Dict, List
from operator import attrgetter

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


class TwitterStore(QStore):

    @staticmethod
    async def fetch_items() -> List[TwitterEntry]:
        try:
            fetch = as_async(api.GetUserTimeline)
            entries = [TwitterEntry(contents=x.text, created_at_in_seconds=x.created_at_in_seconds, created_at=x.created_at, id_str=x.id_str) for x in await fetch(screen_name="@openSUSE")]
            return sorted(entries, key=attrgetter("created_at"))
        except Exception as err:
            await as_async (LOGGER.warning)("Unable to fetch from Twitter @openSUSE: ", err)
            return []

    def filter_fresh_items(self, items: List[TwitterEntry]) -> List[Dict[str, Any]]:
        if not items or not self.container or not self.when_last_update:
            return [i.dict() for i in items]
        return [i.dict() for i in items if getattr(i, "created_at_in_seconds") > datetime.timestamp(self.when_last_update)]


async def search_tweets(keywords: str) -> List[TwitterEntry]:
    try:
        search = as_async(api.GetSearch)
        raw_query = f"q=openSUSE {keywords}&result_type=recent&count=100"
        results = await search(raw_query=raw_query)
        return [TwitterEntry(contents=x.text, created_at_in_seconds=x.created_at_in_seconds, created_at=x.created_at, id_str=x.id_str) for x in results]
    except Exception as err:
        await as_async (LOGGER.warning)("Unable to fetch from Twitter @opensuse: ", err)
        return []


def register_service():
    """
    The idea is that modules are registered against the
    service manager by calling this function. Can be called from @app.on_event('statupp'
    for example, or from somewhere else in __main__, or from TwitterStore. To be discussed,
    but it's flexible enough to work with any decision.
    """
    name = "twitter"
    service_key = name + "_default"
    twitter_strategy = CacheStrategy(
        RedisCacheStrategy(populate_on_startup=True, auto_refresh=True, auto_refresh_delay=300, runner_timeout=None, cache_decay=None), None)
    twitter = ServiceTemplate(name=name, cache_strategy=twitter_strategy,
                              endpoint=None, port=None, credentials=None, custom_parameters=None)
    service = ServicesManager.realize_service_template(
        twitter, TwitterStore(service_key))
    ServicesManager.register_service(name, service)


@app.get(f"/{__MOD_NAME__}/")
async def get_twitter() -> QueryResponse:
    return await Run.query(CacheQuery(service="twitter", item_key="id_str"))


@app.get(f"/{__MOD_NAME__}/search/")
async def search(keywords: str) -> QueryResponse:
    results = await search_tweets(keywords)
    query = Query(service=__MOD_NAME__)
    return QueryResponse(query=query, results=results, results_count=len(results))
