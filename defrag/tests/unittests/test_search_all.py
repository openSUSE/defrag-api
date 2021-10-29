from defrag.modules.db.redis import RedisPool
from defrag.routes import app
from defrag.modules.search_all import search_map
from defrag.modules.docs import set_indexes
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def test_search_map():
    with RedisPool() as conn:
        conn.flushall()
    assert len(search_map) > 0
    print(search_map)


@pytest.mark.asyncio
async def test_set_indexes():
    await set_indexes()


def test_search_all():
    """
    FIX ME
        - searching bugs times out and gets the test to fail.
    """
    response = client.get(
        "/search?keywords=forums&scope=docs,reddit,twitter")
    assert response.status_code == 200
    print(response.json())
