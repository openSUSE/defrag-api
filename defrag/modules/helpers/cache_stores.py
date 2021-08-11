from dataclasses import dataclass
from datetime import datetime
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.data_manipulation import compose
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
from pottery import RedisDeque, RedisDict

# TODO Maybe we want to deprecate this? :) It was a good first pass but I think we have moved along.
"""
r = redis.Redis(host='localhost', port=6379, db=0)


def cache(func):
    @wraps(func)
    def wrapper_func(query: QueryObject, *args, **kwargs):
        if not r.exists(json.dumps(query.context)):
            result = func(query, *args, **kwargs)
            r.set(json.dumps(query.context), json.dumps(result))
            result["cached"] = False
            return result
        else:
            result = json.loads(r.get(json.dumps(query.context)).decode())
            result["cached"] = True
            return result

    return wrapper_func
"""


@dataclass
class Store:
    """
    This is the base class featuring a container type that the 
    subclasses will instantiate as appropriate. The container
    should be a 'pottery cache object' (RedisQueue, RedisDict...) because only then
    can the container perform its caching duty. The base class also features the 
    instant method -- no need to override it -- for searching items in the cache.

    """
    @staticmethod
    async def fetch_items() -> Optional[List[Any]]:
        raise Exception("Override me!")

    container: Iterable

    @as_async
    def search_items(self, item_key: Optional[Union[str, int]] = None, aFilter: Callable = lambda _: True, aSlicer: Callable = lambda xs: xs[:len(xs)], aSorter: Callable = lambda xs: xs) -> List[Any]:
        """ This is made async (= registers as future run in threads) to avoid blocking the events loop """
        slice_then_sort = compose(aSlicer, aSorter)
        if not item_key:
            return slice_then_sort(list(filter(aFilter, self.container)))
        if not isinstance(self.container, Dict):
            raise Exception(
                f"This container type does not support __getitem__: {type(self.container)}")
        return slice_then_sort(list(filter(aFilter, self.container[item_key])))

    @as_async
    def update_container_return_fresh_items(self, items: List[Any]) -> List[Any]:
        """ This is made async (= registers as future run in threads) to avoid blocking the events loop """
        raise Exception(
            "Please override Store.update_container_return_fresh_items!")

    def filter_fresh_items(self, fetch_items: List[Any]) -> List[Any]:
        raise Exception("Please override Store.filter_fresh_items!")

    async def update_on_filtered_fresh(self, items: List[Any]) -> None:
        self.update_container_return_fresh_items(
            self.filter_fresh_items(items))
        return None

class QStore(Store):
    """
    Subclass specializing in 'RedisQueue' cache objects.
    The class takes care of every piece of behaviour
    associated with that cache object.  
    """

    @staticmethod
    async def fetch_items() -> Optional[List[Any]]:
        raise Exception("Please override QStore.filter_fresh_items!")

    def __init__(self, key: str) -> None:
        self.container: RedisDeque = RedisDeque(
            [], key=key, maxlen=1500, redis=RedisPool().connection)
        self.when_last_update: Optional[datetime] = None
        self.when_initialized: datetime = datetime.now()

    @as_async
    def update_container_return_fresh_items(self, items: List[Any]) -> List[Any]:
        """ extendleft() + maxlen work together to append at one end while removing at the other """
        self.container.extendleft(items)
        self.last_update = datetime.now()
        return items

    def filter_fresh_items(self, fetch_items: List[Any]) -> List[Any]:
        raise Exception("Please override QStore.update_container_fresh_items!")


class DStore(Store):
    """
    Subclass specializing in 'RedisDict' cache objects.
    The class takes care of every piece of behaviour
    associated with that cache object.  
    """

    @staticmethod
    async def fetch_items() -> Optional[List[Any]]:
        raise Exception("Please override QStore.filter_fresh_items!")

    def __init__(self, redis_key: str, dict_key: str) -> None:
        self.container: RedisDict = RedisDict(
            [], key=redis_key, redis=RedisPool().connection)
        self.when_last_update: Optional[datetime] = None
        self.when_initialized: datetime = datetime.now()
        self.dict_key = dict_key

    @as_async
    def update_container_return_fresh_items(self, items: List[Any]) -> List[Any]:
        for item in items:
            self.container[getattr(item, self.dict_key)] = item
        self.last_update = datetime.now()
        return items

    def filter_fresh_items(self, fetch_items: List[Any]) -> List[Any]:
        raise Exception("Please override QStore.update_container_fresh_items!")


@dataclass
class RedisCacheStrategy:
    """
    Some settings to be consumed -- immutably -- by the Service Manager when 
    registering services.
    """
    # Whether we should populate the cache ('warm-up') when (re)booting.
    populate_on_startup: bool
    # Whether we should run a background worker to refresh the cache now and then.
    auto_refresh: bool
    # Interveal between runner's runs. (seconds)
    auto_refresh_delay: Optional[int]
    # How much time we should give the runner before timing out (seconds)
    runner_timeout: Optional[int]
    # How much time we should give the corresponding cache before cleaning (seconds)
    cache_decay: Optional[int]


class StoreCacheStrategy:
    """ We probably want to store the keys -- perhaps along with their value -- from our in-memory + redis cache in a backup database.
    That would allow us to repopulate the cache with ease. This would go hand-in-hand with a Cache.MiddleWare.restore method."""

    def __init__(self, *args, **kwargs):
        raise Exception("Not implement 'StoreCacheStrategy")


@dataclass
class CacheStrategy:
    redis: RedisCacheStrategy
    db: Optional[StoreCacheStrategy]


class QueryException(Exception):
    """ We might want to add or override more methods here for better exception handling """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
