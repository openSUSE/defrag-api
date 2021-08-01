from defrag import app
from defrag.modules.helpers import Query
from defrag.modules.helpers.requests import Req
from defrag.modules.helpers.caching import CacheStrategy, QStore, RedisCacheStrategy
from defrag.modules.helpers.data_manipulation import compose
from defrag.modules.helpers.services_manager import Run, ServiceTemplate, ServicesManager
import atoma
from typing import Any, Callable, List, NamedTuple, Optional, Tuple
from collections import namedtuple

""" INFO
This module provides a class to query & store recent reddit posts (sent to "r/openSUSE"). 
Additional features could be:
- posting (would require higher credentials)
- fetching comments 
to model data answering the question: "What are people talking about recently?"
"""

__MOD_NAME__ = "reddit"


class RedditStore(QStore):
    """
    Specialization of QStore to handle specifically data by this service / module.
    """

    def filter_fresh_items(self, items: List[NamedTuple]) -> List[NamedTuple]:
        if not items or not self.container:
            return items
        return [i for i in items if getattr(i, "updated") > self.when_last_update]

    @staticmethod
    async def fetch_items() -> Optional[List[NamedTuple]]:
        """ Tries to fetch 25 most recent posts from r/openSUSE and extract title, url
        and update time in memory """
        def _sort(xs: List[Tuple]) -> List[Tuple]:
            return sorted(xs, key=lambda x: x[2])

        def _make(xs: List[Tuple]) -> List[NamedTuple]:
            entry = namedtuple("RedditPost", ["title", "url", "updated"])
            return list(map(lambda x: entry(x[0], x[1], str(x[2])), xs))

        sort_make: Callable[[List[Any]], List[Any]] = compose(_sort, _make)

        async with Req("https://www.reddit.com/r/openSUSE/.rss") as response:
            try:
                if reddit_bytes := await response.read():
                    feed = atoma.parse_atom_bytes(reddit_bytes)
                    entries: List[Tuple] = [
                        (e.title.value, e.links[0].href, e.updated) for e in feed.entries]
                    return sort_make(entries)
                else:
                    raise Exception("Empty results from r/openSUSE")
            except Exception as err:
                print("Unable to fetch r/openSUSE: ", err)


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


@app.get("/reddit")
async def get_reddit():
    return await Run.query(Query(service="reddit"))
