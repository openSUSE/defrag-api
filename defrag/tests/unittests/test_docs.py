from defrag.modules.db.redis import RedisPool
from defrag.modules.docs import get_data, make_leap_index, ready_to_index, set_indexes
from defrag.routes import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def testing():
    with RedisPool() as conn:
        conn.flushall()
    raw = await get_data("leap")
    idx = make_leap_index(raw)
    print(idx)


@pytest.mark.asyncio
async def test_register():
    await set_indexes()
    assert ready_to_index(["tumbleweed", "leap"])


def test_single_endpoint():
    response = client.get("/docs/search/single/leap/?keywords=zypper")
    assert response.status_code == 200
    results = response.json()["results"]
    print(results)
    assert results


def test_merged_endpoint():
    response = client.get("/docs/search/merged/?keywords=zypper")
    assert response.status_code == 200
    results = response.json()["results"]
    print(results)
    assert results
