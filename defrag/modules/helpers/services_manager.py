from dataclasses import dataclass
from datetime import datetime
from collections import UserDict
from typing import Any, Awaitable, Callable, Dict, List, Optional
from defrag.modules.helpers.cache import CacheMiddleWare, ServiceCacheStrategy


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
    cache: CacheMiddleWare

    async def switchOnOff(self, on: bool) -> None:
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
    services_names = ["twitter_reddit", "bugzilla", "wikis", "mailing_lists",
                      "matrix", "telegram", "pagure", "zypper", "opi", "people", "activities"]

    @classmethod
    def subscribeAll(cls, services: List[Service]) -> None:
        invalid = [s for s in services if not s in cls.services_names]
        if invalid:
            raise Exception(
                f"These services is not implemented: {invalid}")
        names = [s.name for s in services]
        cls.services = Services(names, services)

    @classmethod
    def subscribeOne(cls, service: Service) -> None:
        if not service.name in cls.services_names:
            raise Exception(
                f"This service is not implemented: {service.name}")
        if cls.services:
            cls.services[service.name] = service
        else:
            cls.services = Services([service.name], [service])
        print(
            f"Added service: {service.name}, current services enabled {[s.name for _, s in cls.services.items()]}")
