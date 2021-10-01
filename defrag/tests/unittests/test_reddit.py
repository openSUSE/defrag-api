from defrag import app
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.requests import Req
from defrag.modules.reddit import get_reddit, register_service, search
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)
register_service()


@pytest.mark.asyncio
async def test_reddit_search():
    with RedisPool() as conn:
        conn.flushall()
    res = await search("tux")
    print(res)


@pytest.mark.asyncio
async def test_get_reddit():
    with RedisPool() as conn:
        conn.flushall()
    res = await get_reddit()
    print(res)


def test_reddit_handler():
    with RedisPool() as conn:
        conn.flushall()
    response = client.get("/reddit/")
    assert response.status_code == 200
    print(response.json())


def test_reddit_search_handler():
    with RedisPool() as conn:
        conn.flushall()
    response = client.get("/reddit/search/?keywords=tux")
    assert response.status_code == 200
    print(response.json())
