from defrag.__main__ import startup
from fastapi.testclient import TestClient
from defrag import app
from defrag.modules.helpers.services_manager import ServicesManager
from defrag.modules.helpers.cache import CacheMiddleWare
import pytest

def test_twitter():
    with TestClient(app) as client:
        response = client.get("/twitter")
        services = ServicesManager.services.list_services()
        cache = list(CacheMiddleWare.cache_stores)
        assert len(services) > 0
        assert len(cache) > 0
        assert response.status_code == 200

"""
def test_reddit():
    with TestClient(app) as client:
        response = client.get("/reddit")
        assert response.status_code == 200
"""