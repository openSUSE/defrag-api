from fastapi.testclient import TestClient
from defrag import app


def test_twitter():
    """ FIXME Apparently it does not run with the proper context setup """
    with TestClient(app) as client:
        response = client.get("/twitter")
        assert response.status_code == 200