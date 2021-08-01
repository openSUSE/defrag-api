from defrag import app
from fastapi.testclient import TestClient

def test_twitter():
    with TestClient(app) as client:
        response = client.get("/twitter")
        assert response.status_code == 200

def test_reddit():
    with TestClient(app) as client:
        response = client.get("/reddit")
        assert response.status_code == 200
