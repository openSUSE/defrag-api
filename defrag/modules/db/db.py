from os import environ as env
from typing import Optional, Union
from redis import Redis, BlockingConnectionPool
from redis.client import Pipeline
from pottery import RedisDict


""" 
Using `BlockingConnectionPool` instead of the default
`Redis` object to have some more control over connections and because the default connector 
throws an exception when the pool is exhausted while 
this one simply blocks until a thread becomes available.
Implementing as a context manager to make it very easy to 
customize connections in a fine-grained way (i.e. now we pass different settings
to the context manager instances, or inherit from the class, to handle 
different connection scenarios.) 
"""


class RedisPool:

    pool: Optional[BlockingConnectionPool] = None

    @classmethod
    def open(cls) -> None:
        if not cls.pool:
            print("Opening pool...")
            cls.pool = BlockingConnectionPool(
                host=env["REDIS_HOST"],
                port=env["REDIS_PORT"],
                password=env["REDIS_PWD"],
            )

    @classmethod
    def drain(cls) -> None:
        """ Closes all connections with clients immediately. """
        if cls.pool:
            print("Draining pool...")
            cls.pool.disconnect()
            cls.pool = None

    """
    Pipelines allow for chaining multiple requests and and running them atomically, i.e. so that
    the entire chain either succeeds or fails.
    """

    def __init__(self, pipeline: bool = False) -> None:
        if not RedisPool.pool:
            self.open_pool()
        connector = Redis(connection_pool=self.pool)
        if pipeline:
            self.connection = connector.pipeline()
        else:
            self.connection = connector

    def __enter__(self) -> Union[Redis, Pipeline]:
        return self.connection

    def __exit__(self, *args, **kwargs) -> None:
        return None


def test_RedisPool() -> None:
    print("* * * db.py: Testing * * *")
    with RedisPool() as conn:
        conn.flushall()
        helloworld = RedisDict(
            {"Hello": "World"}, redis=conn, key="helloworld")
        redis_with_pottery = helloworld["Hello"]
        plain_redis = conn.hget("helloworld", key=b'"Hello"').decode(
            "utf-8").replace('"', '')
        assert plain_redis == redis_with_pottery == "World"
    print("* thread pool: OK")
    RedisPool.drain()
    with RedisPool(pipeline=True) as pipeline:
        with pipeline as p:
            p.flushall()
            p.set("Hello", "World")
            p.get("Hello")
            (_, _, res) = p.execute()
            plain_redis = res.decode("utf-8").replace('"', '')
            assert plain_redis == "World"
    print("* pipeline: OK")
    print("* * * db.py: Tests done * * *")
