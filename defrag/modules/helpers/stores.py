from asyncio.tasks import Task
from datetime import datetime
from itertools import islice
from typing import Any, Dict, Generator, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pottery import RedisDeque, RedisDict
from defrag.modules.helpers import CacheQuery

# configuration for the cache store (container)


@dataclass
class ContainerCfg:
    redis_key: str
    # tags which field is to be used as 'id' field when running queries
    id_key: str = "id"
    # tags which field is to be used as 'last updated' field when running queries
    updated_key: str = "updated"

# logs


@dataclass
class Logs:
    logs: List[Dict[str, Any]] = field(default_factory=list)
    last_startup: Optional[float] = None
    last_refresh: Optional[float] = None
    last_eviction: Optional[float] = None
    last_worker_run: Optional[float] = None


class BaseStore(ABC):

    container: Any
    item_id: str
    logs: Logs
    container_config: ContainerCfg

    @abstractmethod
    def to_keep(self, items: List[Any]) -> List[Any]:
        """ Filters out the items that should not be used to update the container. """
        pass

    @abstractmethod
    def to_evict(self) -> List[Any]:
        """ Filters out the items that should be removed from the container """
        pass

    # operations on the cache container

    @abstractmethod
    def update_with(self, items: List[Any]) -> None:
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

    @abstractmethod
    def evict(self) -> None:
        """ Runs the eviction policy on the container. """
        pass

    # concrete method for evaluating a query to the cache

    def evaluate(self, query: CacheQuery) -> List[Any]:
        filtered: Generator[Any, Any, Any]
        if isinstance(self.container, RedisDeque):
            filtered = (x for x in self.container if query.filter_pred(
                x)) if query.filter_pred else (x for x in self.container)
        elif isinstance(self.container, RedisDict):
            if self.item_id:
                return [self.container[self.item_id]] if self.item_id in self.container else []
            filtered = (x for x in self.container.values() if query.filter_pred(
                x)) if query.filter_pred else (x for x in self.container.values())
        else:
            raise Exception(
                f"Cannot evaluate cache query on iterable container of type {type(self.container)}")
        counted = (x for x in islice(filtered, query.count)
                   ) if query.count else filtered
        return sorted(counted, key=lambda item: item[query.sort_on_key], reverse=query.reverse) if query.sort_on_key else sorted(counted, reverse=query.reverse)

    # concrete methods for logging

    def repr(self) -> Dict[str, str]:
        return vars(self)

    def get_logs(self) -> Logs:
        return self.logs

    def log_with(self, message: Dict[str, Any]) -> None:
        self.done = datetime.now().timestamp()
        self.logs.logs.append(message)


# configuration for the worker doing the refresh (if any)

@dataclass
class WorkerCfg:
    worker: bool
    worker_fetch_endpoint: Optional[str]
    worker_interval: Optional[int]
    worker_timeout: Optional[int]


class StoreWorker(ABC):
    worker_config: WorkerCfg

    @abstractmethod
    def create_worker(self) -> Task:
        """
        Returns a handler to an asyncio task that can be stored and cancelled. The
        task is to refresh the cache and to apply the eviction policy.
        """
        pass
