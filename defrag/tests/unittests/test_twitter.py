from defrag.modules.twitter import TwitterStore, register_service, search_tweets
from fastapi.testclient import TestClient
from defrag import app
import pytest

client = TestClient(app)
register_service()


@pytest.mark.asyncio
async def test_get_twitter():
    res = await TwitterStore.fetch_items()
    assert res


@pytest.mark.asyncio
async def test_search():
    res = await search_tweets("rancher")
    assert res


def test_get_twitter_handler():
    response = client.get("/twitter")
    assert response.status_code == 200


def test_get_twitter_search_handler():
    response = client.get("/twitter/search/?keywords=rancher")
    print(response.text)
    assert response.status_code == 200
