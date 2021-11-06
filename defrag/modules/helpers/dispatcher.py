from asyncio.tasks import Task, wait_for
from dataclasses import field
from datetime import datetime
from pottery import RedisSet, RedisDict, RedisDeque
from pydantic import BaseModel
from functools import partial
from typing import Any, Coroutine, Dict, Generator, List, Optional, Tuple, Union
import asyncio

from defrag import LOGGER
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.data_manipulation import schedule_fairly
from defrag.modules.helpers.requests import Session
from defrag.modules.helpers.sync_utils import as_async, run_redis_jobs

__MODULE_NAME__ = "dispatcher"


class Notification(BaseModel):
    body: str
    poll_do_not_push: bool
    dispatched: Optional[float] = None


class EmailNotification(Notification):
    email_address: str
    email_object: str


class MatrixNotification(Notification):
    pass


class TelegramNotification(Notification):
    user_id: Optional[int]
    chat_id: Optional[int]
    bot_endpoint: Optional[str]


class Dispatchable(BaseModel):
    origin: str
    notification: Notification
    retries: int = 0
    schedules: List[float] = []
    id: Optional[int] = None

class HashedDispatchable(Dispatchable):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = abs(hash(datetime.now().timestamp()))
        self.schedules = sorted(self.schedules, reverse=True)


class Dispatcher:
    """
    STRUCTURE
    - Clients can subscribe as pushees, pollers, or both. Subscription is not implemented yet.
    - Pushees should be ready to handle HTTP requests (typically bots running on applications exposing POST endpoints).
    - The Dispatcher acts as message broker that receives 'dispatchables' (i.e. any incoming data payload) on a single async queue, and consumes them as
        either 'schedulables' (dispatchables with an explicit schedule value) or sends them immediately otherwise.
    - The Dispatcher does not handle calendar items (see the 'calendar' module. However it handles the notifications which clients register
        under particular calendar items. In particular, each occurrence -- when calendar items are repeated, i.e. a bi-weekly meeting
        is handled separately.

    TODO:
    - Add functionality for un/subscribing clients.
    - Add confirmation for all new subscriptions, with the confirmation not being a response but a
    call back testing the pushee's endpoint.
    """

    process_q: asyncio.Queue
    running_workers: Dict[str, Task] = {}
    scheduled = RedisDict({}, redis=RedisPool().connection,
                          key="scheduled_items")
    unscheduled_items_ids = RedisSet(
        [], redis=RedisPool().connection, key="unscheduled_items_ids")
    subscribed_pushees = RedisSet(
        [], redis=RedisPool().connection, key="subscribed_pushees")
    subscribed_pollers = RedisSet(
        [], redis=RedisPool().connection, key="subscribed_pollers")
    due_for_polling_notifications = RedisDeque(
        [], redis=RedisPool().connection, key="due_for_polling_notifications")
    due_last_poll: Optional[float] = None

    @classmethod
    def run(cls, seconds: int = 60, dry_run=False) -> None:
        """ 
        Initializes the queue and launch the two consumers. 
        This is made sync to make it easier to use in any context.
        """
        cls.process_q = asyncio.Queue()
        # schedules a task to consume all dispatchables, as they come
        cls.running_workers["processor"] = asyncio.create_task(cls.start_polling_process())
        # schedules a task to consume all and only the 'schedulable' dispatchables,
        # typically calendar notifications, at a  set interval. 1 minute looks OK.
        cls.running_workers["clock"] = asyncio.create_task(cls.start_ticking_clock(seconds, dry_run))

    @classmethod
    def stop(cls) -> None:
        for t in cls.running_workers.values():
            t.cancel()

    @classmethod
    async def put(cls, dispatchable: Union[Dispatchable, Dict[str, Any]]) -> int:
        """ 
        Ensures that the input is a unique dispatchable and puts it into the queue.
        Performance may favor a different way of unpacking the inner dispatchable.
        """
        item = HashedDispatchable(
            **dispatchable.dict()
        ).dict() if isinstance(dispatchable, Dispatchable) else dispatchable
        
        if not "id" in item or not item['id']:
            raise Exception("Cannot process items without id!")
        
        cls.process_q.put_nowait(item)
        return item["id"]

    @classmethod
    async def start_polling_process(cls) -> None:
        """
        Keeps polling 'process_q'.
        """
        LOGGER.info("Started to poll the process queue.")
        while True:
            
            item = await cls.process_q.get()
            
            if not item["schedules"]:
                raise Exception(f"Nothing to schedule on {item}!")
            
            cls.scheduled[item["id"]] = item 
            cls.process_q.task_done()

    @classmethod
    async def start_ticking_clock(cls, interval: int, dry_run: bool) -> None:
        """ 
        On set interval, keep monitoring the 'scheduled' RedisSet.
        Captures and sends items due for dispatching.
        """
        def is_due(float_sched: float) -> bool: 
            return float_sched < datetime.now().timestamp()
            
        while True:
            await asyncio.sleep(3 if dry_run else interval)
            
            due = schedule_fairly(cls.scheduled, key="schedules", filt=is_due)
            await cls.dispatch(due)
            
            if dry_run:
                break

    @classmethod
    async def unschedule(cls, item_id: str) -> None:
        """ Unschedule (marks for cancellation) a scheduled items. """
        found = [k for k in cls.scheduled.keys() if k == item_id]
        
        if found:
            await as_async(cls.unscheduled_items_ids.add)(item_id)

    @classmethod
    async def dispatch(cls, sched: Generator[Tuple[str, float], None, None]) -> None:
        """
        The dispatcher looks up the 'unscheduled' set, to see if the item being processed is found there. 
        - if found, the item is removed from the set and discarded. 
        - if not found, the item is has its notification payload either added to a queue available for external applications to poll, or tried for push/sending.
        - if the push/sending fails, the item is sent to the queue again unless it has been retried 3 times already (discarded if so). 
        - if the sending succeeds, the item is rescheduled if it has remaining scheduled times. Otherwise it is removed from the the scheduled items.
        """
        to_send: List[Coroutine] = []
        redis_jobs: List[partial] = []

        def deleting_key(id: int) -> None:
            cls.scheduled.__delitem__(id)
            LOGGER.info(f"Deleting {id}")

        def removing_from_unscheduled(id: int) -> None:
            cls.unscheduled_items_ids.remove(id)
            deleting_key(id)
            LOGGER.info(f"Removing {id}")

        def polling(item: Dict[str, Any]) -> None:
            item["notification"]["dispatched"] = datetime.now().timestamp()
            cls.due_for_polling_notifications.appendleft(item)
            LOGGER.info(f"Polling {item}")

        """ Dispatching function calls for handling schedules. """
        
        for k, _ in sched:
            item: Dict[str, Any] = cls.scheduled[k]

            if k in cls.unscheduled_items_ids:
                redis_jobs.append(partial(removing_from_unscheduled, item["id"]))
                LOGGER.info(f"To remove {item['id']}")

            if item["notification"]["poll_do_not_push"]:
                redis_jobs.append(partial(polling, item))
                LOGGER.info(f"To poll {item}")
            
            else:
                to_send.append(cls.send(item))
                LOGGER.info(f"To send {item}")
        
        """ Running all tasks involving a network request (pushing). """
        
        for task in asyncio.as_completed(to_send):
            response = await task
            item = response["item"]
            
            if response["status_code"] != 200:

                if response["item"]["retries"] < 2:
                    await as_async(LOGGER.warning)(f"item sending timed out. Retrying soon.")
                    item["retries"] += 1
                    await cls.put(item)

                else:
                    LOGGER.warning(
                        f"Dropping notification {item['notification']} after 3 unsuccessful retries: {item}")

            else:
            
                """ On a successful network request, we remove the schedules. """
                def pop_remove():
                    item["schedules"].pop()
                    if not item["schedules"]:
                        LOGGER.info(f"To delete {item['id']}")
                        deleting_key(item["id"])
                
                redis_jobs.append(partial(pop_remove))
        
        asyncio.create_task(run_redis_jobs(redis_jobs))
        

    @classmethod
    async def poll_due(cls, sync: bool) -> List[Dict[Any, str]]:
        """ 
        Exposes all due schedulables for pollings. When 'sync' is true, performs a destructive sync in the sense that
        all polled items are deleted forever. Else the due schedulables are polled and stay there.
        """
        if not sync or not cls.due_last_poll:
            return list(cls.due_for_polling_notifications)

        def pred(
            item): return item["notification"]["dispatched"] > cls.due_last_poll
        slice = [e for e in cls.due_for_polling_notifications if pred(e)]
        removing_all_due = [
            partial(cls.due_for_polling_notifications.pop) for _ in slice]
        await run_redis_jobs(removing_all_due)
        cls.due_last_poll = datetime.now().timestamp()
        return list(slice)

    @staticmethod
    async def send(item: Dict[str, Any], testing: bool = True) -> Dict[str, Any]:
        """ Sends a dispatched dispatchable to its final destination. """
        if not testing:
            if data := item["requests_options"]["data"]:
                response = await Session().get(item["requests_options"]["url"], json=data)
                return {"status": response.status, "item": item}
        return {"status_code": 200, "item": item}
