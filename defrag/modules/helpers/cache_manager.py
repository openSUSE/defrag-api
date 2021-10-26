from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional
from collections import UserDict

from pottery import RedisDict
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import CacheQuery, QueryResponse
from defrag.modules.helpers.stores import BaseStore
from defrag import LOGGER


@dataclass
class Service:
    """ Meant to be used a mutable service registered against the ServiceManager. """
    started_at: datetime
    store: Optional[BaseStore]
    is_enabled: bool = True
    is_running: bool = True
    shutdown_at: Optional[datetime] = None


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


class Cache:
    """
    This class is supposed to be the core of the application. When registering,
    the services are inserted into the 'services' class attribute.

    The registration is triggered externally (by each module's 'register()' function, but
    it happens here: the registration is just a sequence of function calls that
    take a service name, a'template' (description of settings) and a 'store' (a caching object)
    into an instance of the Services class above. Then each instance of Services can be
    seen as a service running in memory with an active caching behaviour backed up
    by Redis. 
    """
    services = Services({})

    @classmethod
    def register_service(cls, name: str, service: Service) -> None:
        """ 
        Registers a service, making sure en passant that the refreshing worker is being run on time
        and only if it's not running already. 
        """
        cls.services[name] = service
        LOGGER.info("Registered: " + name)


class Memo_Redis:
    
    redicts: Dict[str, RedisDict] = {}

    @staticmethod
    def install_decorator(redict_key: str):
        
        if not redict_key in Memo_Redis.redicts:
            Memo_Redis.redicts[redict_key] = RedisDict(redis=RedisPool().connection, key=redict_key)
        
        def decorator (f: Callable) -> Callable:
            
            @wraps(f)
            async def inner(*args, **kwargs):
                func_call_key = hash(str(f.__name__) + str(args) + str (kwargs))
                if func_call_key in Memo_Redis.redicts[redict_key]:
                    return QueryResponse(**Memo_Redis.redicts[redict_key][func_call_key])
                res: QueryResponse = await f(*args, **kwargs)
                Memo_Redis.redicts[redict_key][func_call_key] = res.dict()
                return res
            return inner
            
        return decorator
        

class Run:
    """
    Async context manager allowing us to visit the cache associated with the service
    responsible for each request. We should write a small 'domain-specific language' for interpreting and evaluating queries here.
    For now we only evaluate them by taking them to visit the cache.
    """

    def __init__(self, query: CacheQuery):
        self.query = query
        self.cache_miss = False

    async def __aenter__(self) -> QueryResponse:
        if not Cache.services:
            raise Exception("Unable to fulfil your request!")
        if not Cache.services[self.query.service].store:
            raise Exception("Service store need to be initialized first.")
        self.results = Cache.services[self.query.service].store.evaluate(self.query)
        if not self.results:
            self.results = await Cache.services[self.query.service].store.fallback(self.query)
            self.cache_miss = True
        if self.results:
            return QueryResponse(query=self.query, results=self.results, results_count=len(self.results))
        return QueryResponse(query=self.query, error="No result found", results=[], result_count=0)
        
    async def __aexit__(self, *args, **kwargs) -> None:
        if self.cache_miss:
            print(f"Cache miss triggering update with {len(self.results)} entries.")
            Cache.services[self.query.service].store.update_with(self.results)
