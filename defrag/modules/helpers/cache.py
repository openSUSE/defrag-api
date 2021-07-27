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
    s


@dataclass
class RedisCacheStrategy:
    reddis_key: str
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

    cache_keys = Cache({"redis_default": RedisDict(
        {}, redis=RedisPool().connection, key="default_cache_middleware")})

    @classmethod
    def get_cache(cls, name: str):
        if not name in cls.cache_keys:
            raise KeyError(
                f"Tried to get cache with a nonexistent name: {name}!")
        return cls.cache_keys[name]

    @classmethod
    def add_cache(cls, name: str, cache: RedisDict):
        if name in cls.cache_keys:
            raise KeyError(
                f"Tried to set cache to an existent value with {name}")
        cls.cache_keys[name] = cache

    @staticmethod
    def validate(query: QueryObject) -> Validation:
        keys = list(query.context.keys())
        key_first = keys[0]
        return Validation(query.context[key_first], [], [])

    @staticmethod
    async def evaluate(validKey: str, strat: RedisCacheStrategy) -> Any:
        if not validKey in CacheMiddleWare.cache_keys:
            res = await strat.runner(validKey)
            CacheMiddleWare.cache_keys[validKey] = res
        return CacheMiddleWare.cache_keys[validKey]

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
