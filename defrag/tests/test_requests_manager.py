from defrag.modules.helpers.requests import Req
import pytest


@pytest.mark.asyncio
async def test_requests_manager():
    async with Req("GET", "https://opensuse-docs-bot.herokuapp.com/stats") as resp:
        assert await resp.text()