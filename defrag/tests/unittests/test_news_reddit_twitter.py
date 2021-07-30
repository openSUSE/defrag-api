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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from defrag.modules.news_reddit_twitter import RedditStore, TwitterStore
import pytest
from sys import stdout

@pytest.mark.asyncio
async def test_redit():
    res = await RedditStore.fetch()
    await RedditStore.refresh(testing=True)
    stdout.write(repr(RedditStore.store.q))
    assert res is not None
    assert len(res) > 0


@pytest.mark.asyncio
async def test_twitter():
    res = await TwitterStore.fetch()
    await TwitterStore.refresh(testing=True)
    stdout.write(repr(TwitterStore.store.q))
    assert res is not None
    assert len(res) > 0
