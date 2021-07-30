# Defrag - centralized API for the openSUSE Infrastructure
# Copyright (C) 2021 openSUSE contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from collections import namedtuple
from defrag.modules.helpers.caching import QStore
from defrag.modules.helpers.data_manipulation import compose
from typing import Any, Callable, List, NamedTuple, Optional, Tuple
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.requests import Req
from os import environ as env
from operator import attrgetter
import atoma
import twitter

""" INFO
This module provides a class -- subclasses 2x below -- to
serve as querying & storing point for recent reddit posts (r/openSUSE)
and tweets (sent by user "@openSUSE"). Additional features could be:
- posting (would require higher credentials)
- fetching also Tweets *about* openSUSE and also Reddit comments 
to model data answering the question: "What are people talking about recently?"
"""

""" TO DO
- [x] Remove 'Req' because it will be used elsewhere  
- [x] ~Add Redis caching => Integrate Redis Caching
"""
__MOD_NAME__ = "news_reddit_twitter"

""" 
The 3 classes below work hand-in-hand to store, fetch and
refresh the last 30 tweets and reddit posts.
"""


class RedditStore(QStore):

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
            entry = namedtuple("TwitterEntry", ["text", "created_at", "id_str"])
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
