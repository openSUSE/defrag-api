from defrag.modules.reddit import get_reddit, search_reddit, register_service
from defrag import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


@pytest.mark.asyncio
async def test_reddit_search():
    res = await search_reddit("tux")
    assert res


@pytest.mark.asyncio
async def test_reddit_new():
    register_service()
    res = await get_reddit()
    assert res


def test_reddit_handler():
    response = client.get("/reddit/")
    assert response.status_code == 200


def test_reddit_search_handler():
    response = client.get("/reddit/search/?keywords=tux")
    assert response.status_code == 200
