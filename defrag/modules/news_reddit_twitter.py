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
from defrag.modules.helpers.caches import QStore
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

    def filter_fresh_items(self, items: List[Any]) -> List[Any]:
        if not items or not self.container:
            return items
        return [i for i in items if getattr(i, "updated") > self.when_last_update]

    @staticmethod
    async def fetch_items() -> Optional[List[NamedTuple]]:
        """ Tries to fetch 25 most recent posts from r/openSUSE and extract title, url
        and update time in memory """
        async with Req("https://www.reddit.com/r/openSUSE/.rss") as response:
            try:
                if reddit_bytes := await response.read():
                    feed = atoma.parse_atom_bytes(reddit_bytes)
                    Entry = namedtuple("Entry", ["title", "url", "updated"])
                    entries: List[Tuple] = [
                        (e.title.value, e.links[0].href, e.updated) for e in feed.entries]

                    def _sort(xs): return sorted(xs, key=attrgetter("updated"))
                    def build_serialize(xs): return list(
                        map(lambda x: Entry(x[0], x[1], str(x[2])), xs))
                    build_serialize_sort: Callable[[List[Any]], List[Any]] = compose(
                        build_serialize, _sort)
                    return build_serialize_sort(entries)
                else:
                    raise Exception("Empty results from r/openSUSE")
            except Exception as err:
                print("Unable to fetch r/openSUSE: ", err)


class TwitterStoring(QStore):

    def filter_fresh_items(self, items: List[Any]) -> List[Any]:
        if not items or not self.container:
            return items
        return [i for i in items if getattr(i, "created_at_in_seconds") > self.when_last_update]

    @staticmethod
    async def fetch_items() -> Optional[List[Any]]:
        # FIX ME: should be Twitter data structure (Status or something)
        try:
            api = twitter.Api(consumer_key=env["TWITTER_CONSUMER_KEY"], consumer_secret=env["TWITTER_CONSUMER_SECRET"],
                              access_token_key=env["TWITTER_ACCESS_TOKEN"], access_token_secret=env["TWITTER_ACCESS_TOKEN_SECRET"])
            
            fetch = as_async(api.GetUserTimeline)
            entries: List[Any] = await fetch(screen_name="@openSUSE")
            return sorted(entries, key=attrgetter("created_at_in_seconds"))
        except Exception as err:
            print("Unable to fetch from Twitter @openSUSE: ", err)
