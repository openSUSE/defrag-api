from defrag import app, pretty_log
from defrag.modules.reddit import register_service as register_reddit
from defrag.modules.twitter import register_service as register_twitter

from fastapi.testclient import TestClient


def test_twitter():
    with TestClient(app) as client:
        register_twitter()
        response = client.get("/twitter")
        assert response.status_code == 200


def test_reddit():
    with TestClient(app) as client:
        register_reddit()
        response = client.get("/reddit")
        assert response.status_code == 200
