from defrag.modules.helpers import Query
from typing import Any, List, NamedTuple, Optional
from os import environ as env
from operator import attrgetter
import twitter
from collections import namedtuple
from defrag import app
from defrag.modules.helpers.caching import CacheStrategy, QStore, RedisCacheStrategy
from defrag.modules.helpers.data_manipulation import compose
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.services_manager import Run, ServiceTemplate, ServicesManager

""" INFO
This module provides a class to
serve as querying & storing point for recent tweets (sent by user "@openSUSE"). 
Additional features could be:
- posting (would require higher credentials)
- fetching also Tweets *about* openSUSE 
to model data answering the question: "What are people talking about recently?"
"""

__MOD_NAME__ = "twitter"


class TwitterStore(QStore):

    def filter_fresh_items(self, items: List[NamedTuple]) -> List[NamedTuple]:
        if not items or not self.container:
            return items
        return [i for i in items if getattr(i, "created_at_in_seconds") > self.when_last_update]

    @staticmethod
    async def fetch_items() -> Optional[List[NamedTuple]]:
        def _sort(xs: List[Any]) -> List[Any]:
            return sorted(xs, key=attrgetter("created_at"))

        def _make(xs: List[Any]) -> List[NamedTuple]:
            entry = namedtuple(
                "TwitterEntry", ["text", "created_at", "id_str"])
            return [entry(x.text, x.created_at, x.id_str) for x in xs]
        sort_make = compose(_sort, _make)
        try:
            api = twitter.Api(consumer_key=env["TWITTER_CONSUMER_KEY"], consumer_secret=env["TWITTER_CONSUMER_SECRET"],
                              access_token_key=env["TWITTER_ACCESS_TOKEN"], access_token_secret=env["TWITTER_ACCESS_TOKEN_SECRET"])

            fetch = as_async(api.GetUserTimeline)
            entries: List[Any] = await fetch(screen_name="@openSUSE")
            return sort_make(entries)
        except Exception as err:
            print("Unable to fetch from Twitter @openSUSE: ", err)


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