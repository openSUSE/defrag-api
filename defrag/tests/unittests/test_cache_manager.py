from defrag import app
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.helpers.cache import Memo
from fastapi.testclient import TestClient
import pytest, asyncio

client = TestClient(app)

@Memo(**{"redict_key": "test_cache_manager", "max_items": 1})
async def decorated(*args, **kwargs) -> QueryResponse:
    return QueryResponse(query=Query(service="test"), results=[{"1":"ok"}])

@pytest.mark.asyncio
async def test_cache_cleaner():
    with RedisPool() as conn:
        conn.flushall()
    print(await decorated())
    print(await decorated(1))
    print(await decorated(3))
    assert len(Memo.redicts["test_cache_manager"].container) == 3
    await Memo.schedule_evict_memo_redis(dry_run=True)
    await asyncio.sleep(4)
    assert len(Memo.redicts["test_cache_manager"].container) == 1
