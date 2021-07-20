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

from asyncio import exceptions
from typing import Optional

from aiohttp.client import ClientSession
from defusedxml.ElementTree import fromstring
import asyncio
import aiohttp

__MOD_NAME__ = "news"


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

    def __init__(self, url, closeOnExit=True):
        if not self.session:
            self.open_session()
        self.url = url
        self.closeOnExit = closeOnExit

    async def __aenter__(self):
        return await self.session.get(self.url)

    async def __aexit__(self, *args, **kwargs):
        if self.closeOnExit:
            await self.close_session()


async def get_reddit_news():
    async with Req("https://www.reddit.com/r/openSUSE/.rss") as response:
        return await response.text()


async def parseIt():
    res = await get_reddit_news()
    root = fromstring(res)
    entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    print(len(entries))

if __name__ == "__main__":
    asyncio.run(parseIt())
