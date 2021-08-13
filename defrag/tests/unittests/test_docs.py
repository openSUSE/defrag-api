import asyncio
from defrag.modules.docs import register, ready_to_index
from defrag import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def test_register():
    register()
    await asyncio.sleep(4)
    assert ready_to_index(["tumbleweed", "leap"])


def test_single_endpoint():
    response = client.get("/docs/single/leap/zypper")
    assert response.status_code == 200
    results = response.json()["results"]
    print(results)
    assert results


def test_merged_endpoint():
    response = client.get("/docs/merged/zypper")
    assert response.status_code == 200
    results = response.json()["results"]
    print(results)
    assert results
