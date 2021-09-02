from defrag.modules.wikis import search_wikis_as_gen
import pytest
from fastapi.testclient import TestClient
from defrag import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_wikis_search():
    res = await search_wikis_as_gen("network")
    assert res


def test_wikis_search_handler():
    response = client.get("/wikis/search/?keywords=network")
    print(response.json())
    assert response.status_code == 200
