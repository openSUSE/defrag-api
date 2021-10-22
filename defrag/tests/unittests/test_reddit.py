from defrag.routes import app
from defrag.modules.db.redis import RedisPool
from defrag.modules.reddit import register_service
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def test_init():
    register_service()
    with RedisPool() as conn:
        conn.flushall()


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
