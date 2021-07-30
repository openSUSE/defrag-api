from dataclasses import dataclass
from datetime import datetime
from collections import UserDict
from defrag.modules.news_reddit_twitter import RedditStore, TwitterStore
from defrag.modules.helpers.data_manipulation import compose
from defrag.modules.helpers import Query, QueryResponse
from typing import Any, Awaitable, Callable, Dict, List, Optional
from defrag.modules.helpers.caching import CacheStrategy, QueryException, RedisCacheStrategy, Store
from defrag import LOGGER, pretty_log


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
    is_enabled: bool
    is_running: bool
    started_at: datetime
    shutdown_at: Optional[datetime]
    cache_store: Store
    controllers: Optional[Controllers]
    template: ServiceTemplate


class Services(UserDict):
    """ A simple mapping from names to Services """

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

    services: Optional[Services] = None
    """ Using the structure below instead of shoving everything to class constructors to
    have a 'dashboard view' of all defaults for all services. """
    services_templates_to_services = {
        "reddit": lambda templ, k, now: Service(True, True, now, None, RedditStore(k), None, templ),
        "twitter": lambda templ, k, now: Service(True, True, now, None, TwitterStore(k), None, templ)
        # ,"bugzilla"
        # ,"wikis"
        # ,"mailing_lists"
        # ,"matrix"
        # ,"telegram"
        # ,"pagure"
        # ,"zypper"
        # ,"opi"
        # ,"people"
        # ,"events"
        # ,"activities"
    }

    @classmethod
    def initialize(cls, *services_templates: ServiceTemplate):
        names = [st.name for st in services_templates]
        invalid = [
            n for n in names if not n in cls.services_templates_to_services]
        if invalid:
            raise Exception(
                f"Tried to register a service that is currently not supported: {str(invalid)}")
        now = datetime.now()
        services = [cls.services_templates_to_services[st.name]
                    (st, st.cache_strategy.redis.redis_key, now) for st in services_templates]
        cls.services = Services(names, services)

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

    class Cache:

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
                diff_then_update = compose(ServicesManager.services[self.query.service].cache_store.filter_fresh_items,
                                           ServicesManager.services[self.query.service].cache_store.update_container_return_fresh_items)
                diff_then_update(self.refreshed_items)
                pretty_log("Cache: Ouch, cache miss on", str(self.query))

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
                    pretty_log("Response", str(len(result)))
                    return QueryResponse(query=query, results_count=len(result))
            else:
                raise QueryException(
                    "No cache strategy for Redis, while Redis is our only caching solution as of your query.")
        except QueryException as err:
            return QueryResponse(query=query, error=f"Unable to satisfy this query for this reason: {err}")
        except Exception as err:
            return QueryResponse(query=query, error=f"A likely programming error occurred: {err}")
