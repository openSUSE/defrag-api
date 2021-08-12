from typing import Any, List
from defrag.modules.helpers.cache_stores import QStore
from defrag.modules.db.redis import RedisPool
import asyncio
import pytest

@pytest.mark.asyncio
async def test_caching():
    with RedisPool() as conn:
        conn.flushall()
    # defining and assigning a key that this container will use to keep in sync with redis
    test_redis_key = "test_redis_key"
    store = QStore(test_redis_key)
    # QStores are built from (empty) RedisDeque. They want to have two methods overriden. Let's
    # override them. 
    async def fetch_items() -> List[Any]:
        print("Faking fetching operation for 2 secs...")
        await asyncio.sleep(2)
        return fake_fetched_items
    def filter_fresh_items(fetch_items: List[Any]) -> List[Any]:
        return list(filter(lambda x:x, fetch_items))
    store.fetch_items = fetch_items 
    store.filter_fresh_items = filter_fresh_items
    fake_fetched_items = [1,2,3]
    # network request returning items available
    fetched_items = await store.fetch_items()
    # keeps only the items more up-to-date than then items already in the container
    # since the container is instantiated empty, that will be all of the new_items
    filtered = store.filter_fresh_items(fetched_items)
    # add the more up-to-date items to the cache, and returning only them in case we'd need to tell the user/client about them
    await store.update_on_filtered_fresh(filtered)
    assert fetched_items == filtered == list(store.container)
