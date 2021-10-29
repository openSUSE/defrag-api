from defrag.routes import app
from defrag.modules.db.redis import RedisPool
from defrag.modules.suggestions import Suggestions
from fastapi.testclient import TestClient
import pytest


@pytest.mark.asyncio
async def test_voting():
    with RedisPool() as conn:
        conn.flushall()
    sugg1 = Suggestions.New(title="Längeren Sommerferien!",
                            description="...", creator_id="user2")
    sugg2 = Suggestions.New(
        title="oS mandatory in every German school", description="...", creator_id="user1")

    result = await Suggestions.add(sugg1)
    if hasattr(result, "ok"):
        await Suggestions.cast_vote("user2", result.ok, 1)
    await Suggestions.add(sugg2)
    res = await Suggestions.view()
    print(result.ok, res)
    assert res


def test_create():
    with RedisPool() as conn:
        conn.flushall()
    with TestClient(app) as client:
        response = client.post(
            "/suggestions/create/", json={"title": "title", "description": "description", "creator_id": "123"})
        print(response)
        assert response.status_code == 200


def test_get():
    with RedisPool() as conn:
        conn.flushall()
    with TestClient(app) as client:
        response = client.get("/suggestions")
        assert response.status_code == 200
