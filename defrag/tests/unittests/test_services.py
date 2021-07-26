from typing import Optional
from defrag.modules.helpers.services_manager import ServicesManager, Service, Controllers
from pottery import RedisDeque
from defrag.modules.db.redis import RedisPool
import pytest
import asyncio


@pytest.mark.asyncio
async def test_cache_manager():
    async def corou1() -> None:
        await asyncio.sleep(2)
        print("ok")
    sm = ServicesManager
    connection = RedisPool(flushOnInit=True).connection
    pottery_primitive = RedisDeque([0], redis=connection, key="test_ok:cache")
    service = Service("telegram", Controllers(corou1, corou1), None,
                      None, None, None, None, None, None, None, None, pottery_primitive)
    sm.subscribeOne(service)
    if tg := sm.services.telegram:
        await tg.switchOnOff(on=True)
        assert tg.is_enabled
        tg.cache.extendleft([1, 2, 3])
        assert list(tg.cache) == [3, 2, 1, 0]
