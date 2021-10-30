from fastapi.testclient import TestClient
from defrag.routes import app

client = TestClient(app)

"""
def test_api_os():
    response = client.get("/obs_packages/search/tumbleweed?keywords=chess")
    assert response.status_code == 200
    print(response.json())
"""
def test_api_os2():
    response = client.get("/obs_packages/search/tumbleweed?keywords=spotify-qt&home_repos=true")
    assert response.status_code == 200
    print(response.json())