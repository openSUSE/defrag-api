from pottery import RedisDict
from defrag.modules.db.redis import RedisPool


def test_redis_conn():
    with RedisPool() as conn:
        conn.flushall()
        helloworld = RedisDict(
            {"Hello": "World"}, redis=conn, key="helloworld")
        redis_with_pottery = helloworld["Hello"]
        plain_redis = conn.hget("helloworld", key=b'"Hello"').decode(
            "utf-8").replace('"', '')
        assert plain_redis == redis_with_pottery == "World"
    RedisPool.drain()


def test_redis_pipe() -> None:
    with RedisPool(pipeline=True) as pipeline:
        with pipeline as p:
            p.flushall()
            p.set("Hello", "World")
            p.get("Hello")
            (_, _, res) = p.execute()
            plain_redis = res.decode("utf-8").replace('"', '')
            assert plain_redis == "World"
    RedisPool.drain()


def test_redis():
    test_redis_conn()
    test_redis_pipe()
