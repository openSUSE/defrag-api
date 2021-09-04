from dataclasses import dataclass
from datetime import datetime
from collections import UserDict
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers import CacheQuery, QueryResponse
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional
from defrag.modules.helpers.cache_stores import CacheStrategy, QueryException, Store
from functools import partial
from defrag import LOGGER
import asyncio


@dataclass
class Controllers:
    """ Some initialization / cleanup helpers doing work outside of the cache_store per se """
    # Must be async
    initializer: Callable
    # Must be async
    shutter: Callable

    def initialize(self) -> Awaitable:
        return self.initializer.__call__()

    def shutdown(self) -> Awaitable:
        return self.shutter.__call__()


@dataclass
class ServiceTemplate:
    """ Meant to be used as an immutable recipe for building a particular service """
    name: str
    cache_strategy: Optional[CacheStrategy]
    endpoint: Optional[str]
    port: Optional[int]
    credentials: Optional[Dict[Any, Any]]
    custom_parameters: Optional[Dict[Any, Any]]


@dataclass
class Service:
    """ Meant to be used a mutable service registered against the ServiceManager. """
    started_at: datetime
    template: ServiceTemplate
    cache_store: Store
    is_enabled: bool = True
    is_running: bool = True
    shutdown_at: Optional[datetime] = None
    controllers: Optional[Controllers] = None


class Services(UserDict):
    """ A simple mapping from names to Services """

    def __getattr__(self, key: str):
        return self.data[key]

    def __setitem__(self, key: str, item: Service) -> None:
        if not key in self.data:
            super().__setitem__(key, item)
        else:
            raise Exception(
                f"Cannot add a service twice, yet you tried to add {key}")

    def __getitem__(self, key: str) -> Service:
        if not key in self.data:
            raise Exception(f"Tried to access a nonexistent service: {key}")
        else:
            return super().__getitem__(key)

    def list_all(self) -> List[str]:
        return list(self.data.keys())

    def list_on(self, predicate: Callable) -> List[str]:
        return [s.name for s in self.values() if predicate(s)]

    def list_enabled(self) -> List[str]:
        return self.list_on(lambda s: s.is_enabled)


class ServicesManager:
    """
    This class is supposed to be the core of the application. When registering,
    the services are inserted into the 'services' class attribute.

    The registration is triggered externally (by each module's 'register()' function, but
    it happens here: the registration is just a sequence of function calls that
    take a service name, a'template' (description of settings) and a 'store' (a caching object)
    into an instance of the Services class above. Then each instance of Services can be
    seen as a service running in memory with an active caching behaviour backed up
    by Redist. 
    """
    services = Services({})
    monitor_last_run: Optional[datetime] = None
    monitor_is_running: bool = False

    @staticmethod
    def realize_service_template(templ: ServiceTemplate, store: Optional[Store], **init_state_override: Optional[Dict[str, Any]]) -> Service:
        now = datetime.now()
        init_state = {"started_at": now,
                      "template": templ, "cache_store": store}
        if init_state_override:
            init_state = {**init_state, **init_state_override}
        return Service(**init_state)

    @classmethod
    def register_service(cls, name: str, service: Service) -> None:
        """ 
        Registers a service, making sure en passant that the refreshing worker is being run on time
        and only if it's not running already. 
        """
        # if not cls.services.keys():
        #    asyncio.create_task(cls.start_monitor())
        cls.services[name] = service
        LOGGER.info("Registered: " + name)

    @classmethod
    async def enable_disable(cls, service_name: str, on: bool) -> None:

        if not cls.services:
            raise Exception(
                "You cannot enable or disable a service before Services have been initialized.")
        if not service_name in cls.services:
            raise Exception(f"Service not found: {service_name}")
        if controllers := cls.services[service_name].controllers:
            if on:
                await controllers.initialize()
                cls.services[service_name].is_enabled = True
            else:
                await controllers.shutdown()
                cls.services[service_name].is_enabled = False
        else:
            raise Exception("Cannot switchOnOff without controllers!")

    @classmethod
    async def start_monitor(cls, interval: int = 60) -> None:
        """ 
        Every minute, iterate over all registered services, refreshing all those that want it.
        Acquires and release a 'lock' at the beginning, respectively at the end of the function body.
        """
        async def fetch_then_update(serv_name: str) -> None:
            try:
                if items := await cls.services[serv_name].cache_store.fetch_items():
                    await cls.services[serv_name].cache_store.update_on_filtered_fresh(
                        items)
                    await as_async (LOGGER.info)(f"Monitor: service {serv_name} was refreshed")
                else:
                    await as_async (LOGGER.warning)(
                        f"Monitor: service {serv_name} could not be refreshed, even though no error occurred.")
            except Exception as error:
                await as_async (LOGGER.error)(f"Service {serv_name} threw an error: {error}")
        while True:
            await asyncio.sleep(interval)
            cls.monitor_is_running = True
            if not cls.services:
                return
            tasks: List[Coroutine] = []
            for serv_name, serv in cls.services.items():
                if strat := serv.template.cache_strategy:
                    if strat.autorefresh:
                        tasks.append(fetch_then_update(serv_name))
            await asyncio.gather(*tasks)
            cls.monitor_last_run = datetime.now()
            cls.monitor_is_running = False


class Run:
    """
    This class maintains no inner state, it just holds some stateless functions
    taking a request against and returning a response, but not before traversing the 
    cache corresponding to the service responsible for handling the request.
    """

    class Cache:
        """
        Async context manager allowing us to visit the cache associated with the service
        responsible for each request. We should write a small 'domain-specific language' for interpreting and evaluating queries here.
        For now we only evaluate them by taking them to visit the cache.
        """

        def __init__(self, query: CacheQuery, fallback: Optional[partial]):
            self.query = query
            self.cache = ServicesManager.services[self.query.service].cache_store
            self.runner = fallback or self.cache.fetch_items
            self.refreshed_items: Optional[List[Any]] = None

        async def __aenter__(self) -> List[Any]:
            if not ServicesManager.services:
                raise Exception(
                    "Cache cannot be traversed before Services are initialized")
            if items_from_cache := await ServicesManager.services[self.query.service].cache_store.search_items():
                return items_from_cache
            if fetched_items := await self.runner():
                self.refreshed_items = fetched_items
                return fetched_items
            raise QueryException(
                f"Unable to produce any results from this query. Neither the cache nor the network were able to produce items.")

        async def __aexit__(self, *args, **kwargs) -> None:
            if self.refreshed_items:
                await self.cache.update_on_filtered_fresh(
                    self.refreshed_items)

    @staticmethod
    async def query(query: CacheQuery, fallback: Optional[partial] = None) -> QueryResponse:
        """ Tries to run the given query, doing all the caching work along the way. A 'finally' clause might
        be in order. """
        if not ServicesManager.services:
            raise QueryException(
                "Services need to be initialized before running a query.")
        async with Run.Cache(query, fallback) as results:
            if not isinstance(results, List):
                results = [results]
            return QueryResponse(query=query, results=results, results_count=len(results))
