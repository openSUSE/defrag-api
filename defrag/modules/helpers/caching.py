# Defrag - centralized API for the openSUSE Infrastructure
# Copyright (C) 2021 openSUSE contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass
from datetime import datetime
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.data_manipulation import compose
from typing import Any, Callable, Dict, Iterable, List, Optional, Union
from pottery import RedisDeque

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
    container: Iterable

    def search_items(self, item_key: Optional[Union[str, int]] = None, _filter: Callable = lambda _: True, _slicer: Callable = lambda xs: xs[:len(xs)], _sorter: Callable = lambda xs: xs) -> List[Any]:
        slice_then_sort = compose(_slicer, _sorter)
        if not item_key:
            res= slice_then_sort(list(filter(_filter, self.container)))
            return res
        if not isinstance(self.container, Dict):
            raise Exception(
                f"This container type does not support __getitem__: {type(self.container)}")
        return slice_then_sort(list(filter(_filter, self.container[item_key])))

    def update_container_return_fresh_items(self, items: List[Any]) -> List[Any]:
        raise Exception("Please override Store.update_container_return_fresh_items!")

    def filter_fresh_items(self, fetch_items: List[Any]) -> List[Any]:
        raise Exception("Please override Store.filter_fresh_items!")

    @staticmethod
    async def fetch_items() -> Optional[List[Any]]:
        raise Exception("Override me!")


class QStore(Store):

    def __init__(self, key: str) -> None:
        self.container: RedisDeque = RedisDeque(
            [], key=key, maxlen=1500, redis=RedisPool().connection)
        self.when_last_update: Optional[datetime] = None
        self.when_initialized: datetime = datetime.now()

    def update_container_return_fresh_items(self, items: List[Any]) -> List[Any]:
        """ extendleft() + maxlen work together to append at one end while removing at the other """
        self.container.extendleft(items)
        self.last_update = datetime.now()
        return items

    def filter_fresh_items(self, fetch_items: List[Any]) -> List[Any]:
        raise Exception("Please override QStore.update_container_fresh_items!")

    @staticmethod
    async def fetch_items() -> Optional[List[Any]]:
        raise Exception("Please override QStore.filter_fresh_items!")


@dataclass
class RedisCacheStrategy:
    # The name of the key in memory and in Reddis where the object equipped with the strategy is going to be cached.
    redis_key: str
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


class InMemoryCacheStrategy:
    """ Not sure about this yet """

    def __init__(self, *args, **kwargs):
        raise Exception("Not implemented 'InMemoryCacheStrategy")


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