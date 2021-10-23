from defrag.routes import app
from fastapi.testclient import TestClient

client = TestClient(app)

async def test_global_search():
    response = client.get("/search?keywords=leap&scope=bugs,docs,reddit,twitter,wikis")
    assert response.status_code == 200
    print(f"That's probably going to be a lot of results, you tell me... {len(response.json())}")