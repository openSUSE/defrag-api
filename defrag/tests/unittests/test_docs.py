from defrag.modules.docs import search
from defrag import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


def test_single_search():
    response = client.get("/docs/single/leap/zypper")
    assert response.status_code == 200
    results = response.json()["results"]
    print(results)
    assert results


def test_merged_search():
    response = client.get("/docs/merged/zypper")
    assert response.status_code == 200
    results = response.json()["results"]
    print(results)
    assert results
