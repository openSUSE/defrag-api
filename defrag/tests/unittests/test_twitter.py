from defrag.modules.db.redis import RedisPool
from defrag.modules.twitter import search
from fastapi.testclient import TestClient
from defrag.routes import app
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def test_init():
    with RedisPool() as conn:
        conn.flushall()


@pytest.mark.asyncio
async def test_search():
    res = await search("forums")
    assert res


def test_get_twitter_handler():
    response = client.get("/twitter")
    assert response.status_code == 200


def test_get_twitter_search_handler():
    response = client.get("/twitter/search/?keywords=forums")
    print(response.text)
    assert response.status_code == 200
