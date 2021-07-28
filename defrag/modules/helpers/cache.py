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

import json
from pottery.annotations import JSONTypes
import redis
from collections import UserDict
from dataclasses import dataclass
from functools import wraps
from sys import stdout
from typing import Any, Callable, List, Optional

import redis
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import QueryObject
from pottery import RedisDict

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


@dataclass
class RedisCacheStrategy:
    # The name of the key in memory and in Reddis where the object equipped with the strategy is going to be cached.
    redis_key: str
    # The async function used by the object required with the strategy to refresh its cache.
    refresher: Callable
    # Whether we should populate the cache ('warm-up') when (re)booting.
    populate_on_startup: bool
    auto_refresh: bool
    runner: Callable
    runner_timeout: Optional[int]   # seconds
    cache_decay: Optional[int]    # seconds


class InMemoryCacheStrategy:
    def __init__(self, *args, **kwargs):
        raise Exception("Not implemented 'InMemoryCacheStrategy")


class StoreCacheStrategy:
    def __init__(self, *args, **kwargs):
        raise Exception("Not implement 'InMemoryCacheStrategy")


@dataclass
class CacheStrategy:
    in_memory: Optional[InMemoryCacheStrategy]
    redis: Optional[RedisCacheStrategy]
    store: Optional[StoreCacheStrategy]


@dataclass
class ServiceCacheStrategy:
    available_strategies: List[CacheStrategy]
    current_strategy: CacheStrategy


@dataclass
class Validation:
    key: str
    missing_keys: List[str]
    excessive_keys: List[str]


class QueryException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QueryResponse(UserDict):
    def __init__(self, query: QueryObject, result: Optional[Any]):
        super().__init__({query: query, result: result})


class Cache(UserDict):

    def __getattr__(self, key: str):
        try:
            return self.data[key]
        except KeyError:
            print(f"No match for this cache name: {key}")

    def __setitem__(self, key: str, item: Any) -> None:
        if not key in self.data:
            self.data[key] = item
        else:
            raise KeyError(
                f"Cannot add a cacher container twice, yet you tried to add {key}")

    def __getitem__(self, key: str) -> Any:
        if not key in self.data:
            raise KeyError(
                f"Cannot get cacher {key} as it does not exist in the Cache. Call `Cache.add()` first.")
        else:
            return self.data[key]


class CacheMiddleWare:
    """ The rationale for this class is that the main functions exposed by `pottery`:
    1. don't offer a fine-grained way to refresh the cache on cache misses.
    2. don't offer reusable, customizable containers for caching. For example `redis_cache` shoves everything down the same unique cache, while we
    sometimes would prefer different caches for different services depending on their use and on the data strutures they naturally suggest.
    The approach I am proposing here is, in a nutshell, a factory which allows us to initialize each service with a separate cache container(s) and 
    caching 'strategy'. For illustration I am initializing by default with a RedisDict-based cache. 

    TODO:
        - adapt the class to be used from FastAPI `BackgroundTasks` and `Dependency`
        - make factory for workers (if BackgroundTasks be used to consume RedisCacheStrategy.auto_refresh and if that's useful)
        - implement restoration/cache warmup and more generally consider using a backup DB. 
    """

    cache_services = Cache({"redis_default": RedisDict(
        {}, redis=RedisPool().connection, key="redis_default")})

    @classmethod
    def get_cache(cls, service_key: str) -> Cache:
        if not service_key in cls.cache_services:
            raise KeyError(
                f"Tried to get cache with a nonexistent name: {service_key}!")
        return cls.cache_services[service_key]

    @classmethod
    @as_async_callback
    def set_service_cache(cls, service_key: str, key: str, val: Any) -> None:
        """ The 'as_async_callback` decorator above allows us to run this function as async but without waiting for it.
        (Remember that assignments to RedisDict are blocking.)
        My hope is to be able to return sooner from the caller. """
        cls.cache_services[service_key][key] = val

    @classmethod
    def add_cache(cls, name: str, cache: RedisDict) -> None:
        if name in cls.cache_services:
            raise KeyError(
                f"Tried to set cache to an existent value with {name}")
        cls.cache_services[name] = cache

    @staticmethod
    def validate(query: QueryObject) -> Validation:
        keys = list(query.context.values())
        val = keys[0]
        return Validation(val, [], [])

    @staticmethod
    async def runCacheStrategy(validKey: str, strat: RedisCacheStrategy) -> Any:
        """More could be done here than just refreshing. We could inspect other attributes from RedisCacheStrategy 
        and use timeouts and clean-ups."""
        cache = CacheMiddleWare.get_cache(strat.redis_key)
        if validKey in cache:
            return cache[validKey]
        val = await strat.refresher(validKey)
        CacheMiddleWare.set_service_cache(
            strat.redis_key, validKey, val)
        return val

    @staticmethod
    async def runQuery(query: QueryObject, redis_strat: RedisCacheStrategy) -> QueryResponse:
        try:
            valid = CacheMiddleWare.validate(query)
            stdout.write("Testing validation")
            if valid.key and not valid.missing_keys + valid.excessive_keys:
                res = await CacheMiddleWare.evaluate(valid.key, redis_strat)
                return QueryResponse(query=query, result=res)
            else:
                raise QueryException(
                    f"Unable to validate your query, check that the following fields are not missing or not in excess: {str(valid.excessive_keys + valid.missing_keys)}")
        except QueryException as err:
            response = QueryResponse(
                query, f"Unable to satisfy this query: {query}")
            return response
        except Exception as err:
            response = QueryResponse(
                query, f"A likely programming error occurred: {err}, so that we were not able to satisfy this request: {query}")
            return response
