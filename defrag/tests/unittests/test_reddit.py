from defrag.routes import app
from defrag.modules.db.redis import RedisPool
from fastapi.testclient import TestClient

client = TestClient(app)

def test_reddit_handler():
    with RedisPool() as conn:
        conn.flushall()
    response = client.get("/reddit/")
    assert response.status_code == 200
    print(response.json())


def test_reddit_search_handler():
    with RedisPool() as conn:
        conn.flushall()
    response = client.get("/reddit/search/?keywords=tux")
    assert response.status_code == 200
    print(response.json())
