from defrag.modules.wikis import search_wikis_as_gen
from fastapi.testclient import TestClient
from defrag.routes import app

import pytest

client = TestClient(app)

@pytest.mark.asyncio
async def test_wikis_search():
    res = await search_wikis_as_gen("network")
    assert res

def test_search_wikis():
    response = client.get("/wikis/search/?keywords=microos")
    print(response.json())
    assert response.status_code == 200
