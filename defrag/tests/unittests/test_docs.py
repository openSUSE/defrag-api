from defrag.modules.docs import get_data, make_leap_index, register_service, ready_to_index
from defrag.routes import app
from fastapi.testclient import TestClient

import asyncio
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def testing():
    raw = await get_data("leap")
    idx = make_leap_index(raw)
    print(idx)


@pytest.mark.asyncio
async def test_register():
    register_service()
    await asyncio.sleep(4)
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
