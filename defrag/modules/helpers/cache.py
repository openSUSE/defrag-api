from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from itertools import islice
from asyncio.tasks import Task
import asyncio
from pottery import RedisDict


from defrag import LOGGER
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import CacheQuery, QueryResponse
from defrag.modules.helpers.stores import BaseStore, StoreWorkerMixin
from defrag.modules.helpers.sync_utils import as_async


class Stores:
    """
    Manages stores 
    """
    # instances of BaseStore holding data for modules that use the
    # '@Stores' decorator. 
    stores: Dict[str, BaseStore] = {}    
    # 1 day in seconds
    interval: int = 86400
    # coroutine object for handling resuming/cancelling
    eviction_worker: Optional[Task] = None
    # last time the worker ran
    last_eviction: Optional[datetime] = None

    class Run:
        """
        Async context manager to visit the 'cache stores' from the 
        parent class.
        """

        def __init__(self, query: CacheQuery) -> None:
            self.query = query
            self.refresh_results: List[Any] = []

        async def __aenter__(self) -> List[Any]:
            
            if not Stores.stores:
                raise Exception("Unable to fulfil your request!")
            
            if results := Stores.stores[self.query.service].evaluate(self.query):
                return results
            
            if results := await Stores.stores[self.query.service].fallback(self.query):
                self.refresh_results = results
                return results
            
            return []

        async def __aexit__(self, *args, **kwargs) -> None:
            if self.refresh_results:
                print(f"Cache miss triggering update with {len(self.refresh_results)} entries.")
                asyncio.create_task(Stores.stores[self.query.service].update_with(self.refresh_results))

    @staticmethod
    async def run(query: CacheQuery) -> List[Any]:
        """ Simple helper to avoid polluting the application's endpoints. """
        async with Stores.Run(query) as response:
            return response

    @classmethod
    def __new__(cls, *args, **kwargs) -> Callable:
        """
        Decorator setting up the appropriate evaluation context
        for queries against 'cache stores'.
        """
        store_key: str = kwargs['store_key']
        
        if not store_key in cls.stores:
            builder: Callable[[], BaseStore] = kwargs['builder']
            store = builder()
            cls.stores[store_key] = store
            print(f"Added store with key: {store.container_config}")

        def decorator(f: Callable) -> Callable:
            @wraps(f)
            async def inner(*args, **kwargs):
                return await f(*args, **kwargs)
            return inner
        return decorator

    @classmethod
    async def evict(cls) -> None:
        """ 'Worker'-coroutine evicting keys every interval. """
        now = datetime.now()
        tasks = []
        
        for k, w in ((k, s) for k, s in cls.stores.items() if isinstance(s, StoreWorkerMixin)):
            if not w.worker_cfg.worker_interval or w.worker_cfg.worker_interval == 0:
                raise Exception(
                    f"The configuration for service {k} has a 0 eviction interval!: {w.worker_cfg}"
                )
            if not cls.last_eviction or now < timedelta(seconds=w.worker_cfg.worker_interval) + cls.last_eviction:
                tasks.append(w.run_worker())
        
        for t in asyncio.as_completed(tasks):
            try:
                await t
            except Exception as error:
                LOGGER.log(
                    msg=f"An exception occurred during {cls.__name__}'s evict method: {error}", level=3)

    @classmethod
    async def start_evict_store_redis(cls, dry_run: bool = False) -> None:
        """ 
        Runner for the above. 
        A dry run means that the worker is going to run just once, in a blocking fashion.
        Otherwise the worker keep running at a set interval.
        """
        if cls.eviction_worker:
            raise Exception ("Worker for evicting redis stores exists already. Please cancel it before starting a new worker.")
        
        if dry_run:
            await cls.evict()
            return

        async def evict_store_redis():
            while True:
                await asyncio.sleep(cls.interval)
                await cls.evict()
                cls.last_eviction = datetime.now()
        
        cls.eviction_worker = asyncio.create_task(evict_store_redis())

    @classmethod
    async def stop_evict_store_redis(cls) -> None:
        if not cls.eviction_worker:
            raise Exception(
                f"{cls.__name__} cannot destroy the memo eviction worker, but that does not exist yet.")
        
        cls.eviction_worker.cancel()
        
        try:
            await cls.eviction_worker
        except asyncio.CancelledError:
            cls.eviction_worker = None
            print(f"{cls.__name__} successfully cancelled & destroyed memo eviction worker .")


class Memo:
    """
    See 'Store' for the documentation as it is mostly identical.
    """

    @dataclass
    class Store:
        redict_key: str
        max_keys: int
        container: RedisDict = field(default_factory=RedisDict)
        hits: Dict[int, int] = field(default_factory=Dict)

    redicts: Dict[str, Store] = {}
    interval: int = 86400
    last_eviction: Optional[datetime] = None
    eviction_worker: Optional[Task] = None

    @classmethod
    def __new__(cls, *args, **kwargs) -> Callable:
        """ 
        Overloading class initialization with a decorator setting up
        the context for evaluating memorized queries.
        """
        memo_key: str = kwargs["memo_key"]

        if not memo_key in cls.redicts:
            
            cls.redicts[memo_key] = cls.Store(
                redict_key=memo_key,
                container=RedisDict(key=memo_key, redis=RedisPool().connection),
                hits=dict(),
                max_keys=kwargs.get("max_keys", 50)
            )
            print(f"Memo registered {memo_key}.")

        def decorator(f: Callable) -> Callable:
            
            @wraps(f)
            async def inner(*args, **kwargs):
                func_call_key = hash(f"{f.__name__}{args}{kwargs}")

                if func_call_key in cls.redicts[memo_key].container:
                    
                    if func_call_key in cls.redicts[memo_key].hits:
                        cls.redicts[memo_key].hits[func_call_key] += 1
                    
                    else:
                        cls.redicts[memo_key].hits[func_call_key] = 1
                    
                    return QueryResponse(**cls.redicts[memo_key].container[func_call_key])
                
                res: QueryResponse = await f(*args, **kwargs)
                cls.redicts[memo_key].container[func_call_key] = res.dict()
                return res
            
            return inner
        return decorator

    @classmethod
    async def evict(cls) -> None:
        """
        Evicts all keys from the memoizing cache
        container if not among the 50 most demanded keys.
        """
        for k, store in cls.redicts.items():
            
            most_hits = (x for x in islice(sorted({k: v for k, v in store.container.items()}, reverse=True), store.max_keys))
            new_container = {k: v for k, v in store.container.items() if k in most_hits}
            cls.redicts[k].hits.clear()
            await as_async(cls.redicts[k].container.clear)()
            cls.redicts[k].container = RedisDict(new_container, key=cls.redicts[k].redict_key, redis=RedisPool().connection)
        
        cls.last_eviction = datetime.now()

    @classmethod
    async def schedule_evict_memo_redis(cls, dry_run: bool = False) -> None:
        if cls.eviction_worker:
            raise Exception ("Worker for evicting redis stores exists already. Please cancel it before starting a new worker.")

        if dry_run:
            await cls.evict()
            return

        async def evict_memo_redis():
            while True:
                await asyncio.sleep(cls.interval)
                await cls.evict()
                cls.last_eviction = datetime.now()
        
        cls.eviction_worker = asyncio.create_task(evict_memo_redis())

    @classmethod
    async def stop_evict_memo_redis(cls) -> None:
        if not cls.eviction_worker:
            raise Exception(
                f"{cls.__name__} cannot destroy the memo eviction worker, but that does not exist yet.")
        
        cls.eviction_worker.cancel()
        
        try:
            await cls.eviction_worker
        except asyncio.CancelledError:
            cls.eviction_worker = None
            print(f"{cls.__name__} successfully cancelled & destroyed memo eviction worker .")



