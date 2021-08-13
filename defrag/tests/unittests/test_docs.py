from defrag import app
from defrag.modules.docs import search_single_source_docs
from fastapi.testclient import TestClient

client = TestClient(app)

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