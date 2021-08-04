from defrag.modules.helpers.requests import Req
import pytest


@pytest.mark.asyncio
async def test_requests():
    async with Req("https://opensuse-docs-bot.herokuapp.com/stats") as resp:
        assert await resp.text()