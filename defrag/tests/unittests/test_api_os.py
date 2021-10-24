from fastapi.testclient import TestClient
from defrag.routes import app

client = TestClient(app)

def test_api_os():
    response = client.get("/api_os/search/tumbleweed?keywords=chess")
    assert response.status_code == 200
    print(response.json())