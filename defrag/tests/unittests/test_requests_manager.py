import asyncio
from defrag.modules.helpers.requests import Session
import pytest


async def go(i: int):
    await Session().get("https://opensuse-docs-bot.herokuapp.com/stats")
    await asyncio.sleep(100e-3)
    return i


@pytest.mark.asyncio
async def test_requests_manager():
    results = [x for x in await asyncio.gather(*[go(x) for x in range(0, 100)])]
    assert results == [x for x in range(0, 100)]
