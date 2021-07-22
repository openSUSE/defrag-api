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

from typing import List, NamedTuple, Optional, Tuple
from aiohttp.client import ClientSession
from datetime import datetime, timedelta
from collections import namedtuple, deque
from operator import attrgetter
import atoma
import asyncio
import aiohttp

__MOD_NAME__ = "reddit_news"

# FIX ME: Replace with real cache
my_reddis_news_cache = {"entries": None,
                        "last_updated": None, "delta": timedelta(minutes=5)}


class Req:

    session: Optional[ClientSession] = None

    @classmethod
    def open_session(cls):
        if not cls.session:
            cls.session = aiohttp.ClientSession()

    @classmethod
    async def close_session(cls):
        if cls.session and not cls.session.closed:
            await cls.session.close()

    def __init__(self, url: str, closeOnExit: bool = True):
        if not self.session:
            self.open_session()
        self.url = url
        self.closeOnExit = closeOnExit

    async def __aenter__(self):
        return await self.session.get(self.url)

    async def __aexit__(self, *args, **kwargs):
        if self.closeOnExit:
            await self.close_session()


def reddit_atom_parser(reddit_bytes: bytes) -> Tuple[List[NamedTuple], Optional[datetime]]:
    feed = atoma.parse_atom_bytes(reddit_bytes)
    Entry = namedtuple("Entry", ["title", "url", "updated"])
    entries: List[NamedTuple] = [Entry(e.title.value, e.links[0].href, e.updated)
                                 for e in feed.entries]
    return (entries, feed.updated)


async def get_reddit_news() -> Optional[Tuple[List[NamedTuple], Optional[datetime]]]:
    async with Req("https://www.reddit.com/r/openSUSE/.rss") as response:
        try:
            if res := reddit_atom_parser(await response.read()):
                entries, updated = res
                return (sorted(entries, key=attrgetter("updated"), reverse=True), updated)
        except Exception as error:
            print(
                f"Failed to fetch & parse r/openSUSE/.rss for this reasons: {error}")


async def autorefresh() -> None:
    print("Refreshing cache from with r/openSUSE/.rss now...")
    now = datetime.now()
    q = my_reddis_news_cache["entries"]
    if res := await get_reddit_news():
        entries, _ = res
        if not q or len(q) == 0:
            my_reddis_news_cache["entries"] = deque(entries, maxlen=30)
            my_reddis_news_cache["last_updated"] = now
            print(f"Autorefreshed {len(entries)} entries from r/openSUSE/.rss")
            return
        if now - my_reddis_news_cache["last_updated"] > my_reddis_news_cache["delta"]:
            fresher = list(filter(lambda x: x > q[0], entries))
            for i in fresher:
                q.appendLeft(i)
                q.pop()
            my_reddis_news_cache["entries"] = q
            my_reddis_news_cache["last_updated"] = now
            print(f"Autorefreshed {len(fresher)} entries from r/openSUSE/.rss")
    await asyncio.sleep(300)
    asyncio.create_task(autorefresh())

if __name__ == "__main__":
    asyncio.run(autorefresh())
