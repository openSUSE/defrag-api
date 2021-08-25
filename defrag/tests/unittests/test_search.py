from defrag.modules.search import global_search
from defrag import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)

@pytest.mark.asyncio
async def test_global_search():
    response = await global_search(keywords="leap", scope="bugs, docs, reddit, twitter, wikis")
    print(f"That's probably going to be a lot of results, you tell me... {response.results_count}")
    assert response