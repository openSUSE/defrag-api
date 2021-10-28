from defrag.routes import app
from defrag.modules.search import search_map
from defrag.modules.docs import set_indexes
from fastapi.testclient import TestClient
import asyncio
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def test_search_map():
    assert len(search_map) > 0
    print(search_map)
    await set_indexes()


def test_global_search():
    response = client.get(
        "/search?keywords=leap&scope=bugs,docs,reddit,twitter,wikis")
    assert response.status_code == 200
    print(response.json())
