from defrag import app
from fastapi.testclient import TestClient
import sys

def test_twitter():
    with TestClient(app) as client:
        response = client.get("/twitter")
        sys.stdout.write(str(response.json()))
        assert response.status_code == 404

def test_reddit():
    with TestClient(app) as client:
        response = client.get("/reddit")
        sys.stdout.write(str(response.json()))
        assert response.status_code == 404
