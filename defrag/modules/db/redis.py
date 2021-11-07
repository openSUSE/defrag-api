from typing import Optional, Union
from redis import Redis, BlockingConnectionPool
from redis.client import Pipeline
from defrag import config, LOGGER

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
            LOGGER.debug("Opening pool...")
            cls.pool = BlockingConnectionPool(
                host=config["REDIS_HOST"],
                port=config["REDIS_PORT"],
                password=config["REDIS_PWD"],
            )

    @classmethod
    def get(cls, pipeline: bool = False):
        if not cls.pool:
            cls.open()
        return cls(pipeline)

    @classmethod
    def drain(cls) -> None:
        """ Closes all connections with clients immediately. """
        if cls.pool:
            LOGGER.debug("Draining pool...")
            cls.pool.disconnect()
            cls.pool = None

    """
    Pipelines allow for chaining multiple requests and and running them atomically, i.e. so that
    the entire chain either succeeds or fails.
    """

    def __init__(self, pipeline: bool = False, flushOnInit:bool = False) -> None:
        if not RedisPool.pool:
            self.open()
        redis_conn = Redis(connection_pool=self.pool)
        if pipeline:
            self.connection = redis_conn.pipeline()
        else:
            self.connection = redis_conn
        if flushOnInit:
            self.connection.flushall()

    def __enter__(self) -> Union[Redis, Pipeline]:
        return self.connection

    def __exit__(self, *args, **kwargs) -> None:
        return None
