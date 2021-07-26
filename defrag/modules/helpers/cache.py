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

import asyncio
import json
from collections import UserDict
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional, Union
from pottery.exceptions import KeyExistsError

import redis
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import QueryObject
from pottery import RedisDict, RedisDeque, RedisSet

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
class Strategy:
    key: str
    is_enabled: bool
    populate_on_startup: bool
    auto_refresh: bool
    cache_decay: int    # seconds
    fallback_timeout: int   # seconds


@dataclass
class CacheStrategies:
    in_memory: Strategy
    redis: Strategy
    store: Strategy


@dataclass
class ServiceCacheStrategy:
    available_strategies: List[CacheStrategies]
    current_strategy: CacheStrategies


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

    cache = Cache({"redis_default": RedisDict(
        {}, redis=RedisPool().connection, key="default_cache_middleware")})

    @classmethod
    def get_cache(cls, name: str):
        if not name in cls.cache:
            raise KeyError(
                f"Tried to get cache with a nonexistent name: {name}!")
        return cls.cache[name]

    @classmethod
    def add_cache(cls, name: str, cache: RedisDict):
        if name in cls.cache:
            raise KeyError(
                f"Tried to set cache to an existent value with {name}")
        cls.cache[name] = cache

    @staticmethod
    def validate(query: QueryObject) -> Validation:
        return Validation("Go!", [], [])

    @staticmethod
    def fromCache(key, redis_strat: Strategy):
        cache = CacheMiddleWare.cache[redis_strat.key]
        return cache[key]

    @staticmethod
    async def runFallback(query: QueryObject, valid_key: str, strat: Strategy) -> Any:
        async def callback(query):
            await asyncio.sleep(1)
            return "Hey, I am mocking fallback's result."
        res = await callback(query)
        cache = CacheMiddleWare.cache[strat.key]
        cache[valid_key] = res
        return res

    @staticmethod
    async def runQuery(query: QueryObject, redis_strat: Strategy) -> QueryResponse:
        try:
            validation = CacheMiddleWare.validate(query)
            if validation.key and not validation.missing_keys + validation.excessive_keys:
                if validation.key in CacheMiddleWare.cache:
                    return QueryResponse(query, result=CacheMiddleWare.fromCache(validation.key, redis_strat))
                elif res_fallback := await CacheMiddleWare.runFallback(query, validation.key, redis_strat):
                    return QueryResponse(query=query, result=res_fallback)
                else:
                    raise QueryException(
                        f"Unable to find a fallback for this query, which the cache could not satisfy: {str(query)}")

            else:
                raise QueryException(
                    f"Unable to validate your query, check that the following fields are not missing or not in excess: {str(validation.excessive_keys + validation.missing_keys)}")
        except QueryException as err:
            response = QueryResponse(
                query, f"Unable to satisfy this query: {query}")
            return response
        except Exception as err:
            response = QueryResponse(
                query, f"A likely programming error occurred: {err}, so that we were not able to satisfy this request: {query}")
            return response
