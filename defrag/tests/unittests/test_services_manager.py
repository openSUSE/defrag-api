from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.caching import RedisCacheStrategy
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.services_manager import Run
from defrag.modules.reddit import register_service as register_reddit
from defrag.modules.twitter import register_service as register_twitter
import pytest

"""
Admittedly not very detailed, if you guys need me to unpack all the intermediary
steps, let me know.
"""


@pytest.mark.asyncio
async def test_reddit_service():
    with RedisPool() as connection:
        connection.flushall()
    register_reddit()
    query = Query(service="reddit")
    res: QueryResponse = await Run.query(query)
    assert res.results_count == 25


@pytest.mark.asyncio
async def test_twitter_service():
    with RedisPool() as connection:
        connection.flushall()
    register_twitter()
    query = Query(service="twitter")
    res: QueryResponse = await Run.query(query)
    assert res.results_count == 20
