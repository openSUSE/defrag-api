from fastapi.testclient import TestClient
from defrag.routes import app

client = TestClient(app)

def test_flathub():
    response = client.get("/flathub/apps/search?keywords=vlc")
    assert response.status_code == 200
    print(response.json())