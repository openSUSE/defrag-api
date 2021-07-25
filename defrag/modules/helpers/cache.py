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

"""from defrag.modules.helpers import QueryObject
from defrag.modules.db.redis import RedisPool
"""
from typing import Any, Awaitable, Callable, Dict, List, Optional
from pottery import RedisDict, RedisDeque, RedisCounter, RedisList, RedisSet
import redis
import json
from functools import wraps
from dataclasses import dataclass
from datetime import datetime
from collections import UserDict

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
class Strategy:
    is_enabled: bool
    populate_on_startup: bool
    auto_refresh: bool


@dataclass
class CacheStrategies:
    in_memory: Strategy
    redis: Strategy


@dataclass
class ServiceCacheStrategy:
    available_strategies: List[CacheStrategies]
    current_strategy: CacheStrategies


@dataclass
class Controllers:
    _initializer: Callable
    _shutter: Callable

    def initialize(self) -> Awaitable:
        return self._initializer.__call__()

    def shutdown(self) -> Awaitable:
        return self._shutter.__call__()


@dataclass
class Service:
    name: str
    controllers: Controllers
    started_at: Optional[datetime]
    shutdown_at: Optional[datetime]
    is_enabled: Optional[bool]
    is_running: Optional[bool]
    endpoint: Optional[str]
    port: Optional[int]
    credentials: Optional[Dict[Any, Any]]
    custom_parameters: Optional[Dict[Any, Any]]
    cache_strategy: Optional[ServiceCacheStrategy]
    cache: Any

    async def switch(self, on: bool) -> None:
        try:
            if on:
                await self.controllers.initialize()
                self.is_enabled = True
                print(f"Enabled: {self.name}")
            else:
                await self.controllers.shutdown()
                self.is_enabled = False
                print(f"Turned off: {self.name}")
        except Exception as err:
            print(
                f"Failed to enable this service: {self.name} for this reason {err}")


class Services(UserDict):

    def __init__(self, names: List[str], services: List[Service]):
        super().__init__(dict(zip(names, services)))

    def __getattr__(self, key: str):
        try:
            return self.data[key]
        except KeyError:
            print(f"No match for this service name: {key}")

    def __setitem__(self, key: str, item: Service) -> None:
        if not key in self.data:
            super().__setitem__(key, item)
        else:
            raise Exception(
                f"Cannot add a service twice, yet you tried to add {key}")


class ServicesManager:

    services: Optional[Services] = None
    services_names: List[str] = ["twitter_reddit", "bugzilla", "wikis", "mailing_lists",
                                 "matrix", "telegram", "pagure", "zypper", "opi", "people", "activities"]

    @classmethod
    def init_all(cls, services: List[Service]) -> None:
        invalid = [s for s in services if not s in cls.services_names]
        if invalid:
            raise Exception(
                f"These services is not implemented: {invalid}")
        names = [s.name for s in services]
        cls.services = Services(names, services)

    @classmethod
    def add(cls, service: Service) -> None:
        if not service.name in cls.services_names:
             raise Exception(
                f"This service is not implemented: {service.name}")
        if cls.services:
            cls.services[service.name] = service
        else:
            cls.services = Services([service.name], [service])
        print(
            f"Added service: {service.name}, current services enabled {[s.name for _, s in cls.services.items()]}")