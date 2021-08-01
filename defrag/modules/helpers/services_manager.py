from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import UserDict
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.data_manipulation import compose
from defrag.modules.helpers import Query, QueryResponse
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional
from defrag.modules.helpers.caching import CacheStrategy, QueryException, RedisCacheStrategy, Store
from defrag import LOGGER, pretty_log
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
    cache_strategy: CacheStrategy
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

    def __getitem__(self, key: str) -> Service:
        if not key in self.data:
            raise Exception(f"Tried to access a nonexistent service: {key}")
        else:
            return super().__getitem__(key)

    def list_all(self) -> List[str]:
        return list(self.data.keys())

    def list_on(self, predicate: Callable) -> List[str]:
        return [s.name for s in self.values() if predicate(s)]


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
    auto_refresh_worker_last_run: Optional[datetime] = None
    auto_refresh_worker_locked = False

    @staticmethod
    def realize_service_template(templ: ServiceTemplate, store: Store, **init_state_override: Optional[Dict[str, Any]]) -> Service:
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
        cls.services[name] = service
        pretty_log("Registered: ", name)
        now = datetime.now()
        if cls.auto_refresh_worker_locked:
            return
        if not cls.auto_refresh_worker_last_run or (now - cls.auto_refresh_worker_last_run > timedelta(seconds=60)):
            asyncio.create_task(Run.autorefresh_services_stores())

    @classmethod
    async def enable_disable(cls, service_name: str, on: bool) -> None:
        try:
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
        except Exception as err:
            LOGGER.warning(
                f"Failed to enable this service: {service_name} for this reason {err}")


class Run:
    """
    This class maintains no inner state, it just holds some stateless functions
    taking a request against and returning a response, but not before traversing the 
    cache corresponding to the service responsible for handling the request.
    """

    class Cache:
        """
        Async context manager allowing us to visit the cache associated with the service
        responsible for each request.
        """

        def __init__(self, query: Query, strategy: RedisCacheStrategy):
            self.strategy = strategy
            self.query = query
            self.refreshed_items: Optional[List[Any]] = None

        async def __aenter__(self) -> List[Any]:
            if not ServicesManager.services:
                raise Exception(
                    "Cache cannot be traversed before Services are initialized")
            if items_from_cache := ServicesManager.services[self.query.service].cache_store.search_items():
                return items_from_cache
            if fetched_items := await ServicesManager.services[self.query.service].cache_store.fetch_items():
                self.refreshed_items = fetched_items
                return fetched_items
            return []

        async def __aexit__(self, *args, **kwargs) -> None:
            if not ServicesManager.services:
                raise Exception(
                    "CacheTraveller has nothing to travel if Services are not initialized")
            if self.refreshed_items:
                ServicesManager.services[self.query.service].cache_store.update_on_filtered_fresh(
                    self.refreshed_items)
                pretty_log("Cache: Ouch, cache miss on", str(self.query))

    @staticmethod
    async def autorefresh_services_stores(interval: int = 60) -> None:
        """ 
        Every minute, iterate over all registered services, refreshing all those that want it.
        Acquires and release a 'lock' at the beginning, respectively at the end of the function body.
        """
        ServicesManager.auto_refresh_worker_locked = True
        await asyncio.sleep(interval)
        if not ServicesManager.services:
            return
        tasks: List[Coroutine] = []

        async def fetch_then_update(serv_name: str) -> Dict[str, str]:
            try:
                if items := await ServicesManager.services[serv_name].cache_store.fetch_items():
                    ServicesManager.services[serv_name].cache_store.update_on_filtered_fresh(
                        items)
                    return {"service_name": serv_name, "ok": ""}
                return {"service_name": serv_name, "error": "Unable to fetch!"}
            except Exception as error:
                return {"service_name": serv_name, "error": str(error)}

        for serv_name, serv in ServicesManager.services.items():
            if strat := serv.template.cache_strategy:
                if strat.autorefresh:
                    tasks.append(fetch_then_update(serv_name))
        await asyncio.gather(*tasks)
        ServicesManager.auto_refresh_worker_last_run = datetime.now()
        ServicesManager.auto_refresh_worker_locked = False
        asyncio.create_task(Run.autorefresh_services_stores())

    @staticmethod
    async def query(query: Query) -> QueryResponse:
        """ Tries to run the given query, doing all the caching work along the way. A 'finally' clause might
        be in order. """
        if not ServicesManager.services:
            raise QueryException(
                "Services need to be initialized before running a query.")
        try:
            if redis_strat := ServicesManager.services[query.service].template.cache_strategy.redis:
                async with Run.Cache(query, redis_strat) as result:
                    return QueryResponse(query=query, results_count=len(result))
            else:
                raise QueryException(
                    "No cache strategy for Redis, while Redis is our only caching solution as of your query.")
        except QueryException as err:
            return QueryResponse(query=query, error=f"Unable to satisfy this query for this reason: {err}")
        except Exception as err:
            return QueryResponse(query=query, error=f"A likely programming error occurred: {err}")
