import redis
from defrag.modules.helpers.sync_utils import run_redis_jobs
from defrag.modules.db.redis import RedisPool
from defrag import app
from fastapi.testclient import TestClient
from functools import partial
import pytest
from pottery.dict import RedisDict

cient = TestClient(app)
d = RedisDict({}, redis=RedisPool().connection)

def job(k, val):
    d[k] = val

@pytest.mark.asyncio
async def test():
    with RedisPool() as conn:
        conn.flushall()
    j = []
    j.append(partial(job, 1, "ok"))
    j.append(lambda: job(2, "and more"))
    await run_redis_jobs(j)
    for v in d.values():
        print(v)
    assert d == {1: "ok", 2: "and more"}


