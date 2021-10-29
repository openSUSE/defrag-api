import asyncio
from asyncio.tasks import Task, create_task
from datetime import datetime
from itertools import islice
from typing import Any, Callable, Dict, Iterable, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pottery import RedisDeque, RedisDict
from defrag.modules.helpers import CacheQuery


@dataclass
class ContainerCfg:
    """ Configuration for the cache store (container) """

    redis_key: str
    # tags which field is to be used as 'id' field when running queries
    id_key: str = "id"
    # tags which field is to be used as 'last updated' field when running queries
    updated_key: str = "updated"


@dataclass
class Logs:
    """ Logs to the cache store"""

    logs: List[Dict[str, Any]] = field(default_factory=list)
    last_startup: Optional[float] = None
    last_refresh: Optional[float] = None
    last_eviction: Optional[float] = None
    last_worker_run: Optional[float] = None


class BaseStore(ABC):
    """
    Hybrid class declaring instance methods for store self-management
    and also adding a concrete evaluation instance method.
    """

    container: Any
    container_cfg: ContainerCfg
    item_id: str
    logs: Logs
    
    # filtering operations

    @abstractmethod
    def to_keep(self, items: List[Any]) -> List[Any]:
        """ Filters out the items that should not be used to update the container. """
        pass

    # updating operations

    @abstractmethod
    async def update_with(self, items: List[Any]) -> None:
        """ Runs an update to the container."""
        pass

    @abstractmethod
    async def fallback(self, query: CacheQuery) -> List[Any]:
        """ Fall back option in case visiting the cache yields nothing. """
        pass

    @abstractmethod
    async def warmup(self) -> None:
        """ Runs some network action to fetch items and use them to warm up the cache. """
        pass

    @abstractmethod
    async def refresh(self) -> None:
        """ Runs some network action to fetch items and use them to refresh the cache. """
        pass

    # concrete method for evaluating a query to the cache

    def evaluate(self, query: CacheQuery) -> List[Dict[str, Any]]:
        filtered: Iterable

        if isinstance(self.container, RedisDeque):
            filtered = (x for x in self.container if query.filter_pred(
                x)) if query.filter_pred else self.container
        
        elif isinstance(self.container, RedisDict):
            if self.item_id:
                return [self.container[self.item_id]] if self.item_id in self.container else []
            filtered = (x for x in self.container.values() if query.filter_pred(x)) if query.filter_pred else (x for x in self.container.values())
        
        else:
            raise Exception(
                f"Cannot evaluate cache query on iterable container of type {type(self.container)}")
        
        counted = (x for x in islice(filtered, query.count)) if query.count else filtered
        return sorted(counted, key=lambda item: item[query.sort_on_key], reverse=query.reverse) if query.sort_on_key else list(counted)

    # concrete methods for logging

    def get_logs(self) -> Logs:
        return self.logs

    def log_with(self, message: Dict[str, Any]) -> None:
        self.done = datetime.now().timestamp()
        self.logs.logs.append(message)


@dataclass
class WorkerCfg:
    """ Configuration for the worker doing the refreshing (if any). """
    has_worker: bool
    worker_fetch_endpoint: Optional[str]
    worker_interval: Optional[int]
    worker_timeout: Optional[int]


class StoreWorkerMixin:
    """ Mixin for adding "worker-like" (auto-scheduled task) functionality to stores. """
    worker_cfg: WorkerCfg
    worker: Optional[Task]
    logs: Logs
    log_with: Callable
    refresh: Callable

    async def run_worker(self) -> None:
        if not self.worker_cfg.worker_interval:
            raise Exception(
                "Tried to create a worker from TwitterStore, but no worker_cfg.worker interval set.")
        try:
            await asyncio.wait_for(self.refresh(), timeout=self.worker_cfg.worker_timeout)
            self.logs.last_worker_run = datetime.now().timestamp()
        except asyncio.exceptions.TimeoutError:
            self.log_with({"msg": f"timedout after {self.worker_cfg.worker_timeout} seconds."})