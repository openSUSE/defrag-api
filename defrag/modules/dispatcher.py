
from asyncio.tasks import Task, wait_for
from datetime import datetime
from defrag import LOGGER, app
from defrag.modules.helpers import Query, QueryResponse
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.requests import Req
from defrag.modules.helpers.data_manipulation import dropwhile_takeif
from defrag.modules.helpers.sync_utils import as_async, run_redis_jobs
from pottery import RedisSet, RedisDict, RedisDeque
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
import asyncio

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
    id: Optional[str] = None


class HashedDispatchable(Dispatchable):

    id: Optional[int] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = self.id or str(abs(hash(str(self.notification))))
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
    def run(cls, seconds: int = 60) -> None:
        """ 
        Initializes the queue and launch the two consumers. 
        This is made sync to make it easier to use in any context.
        """
        cls.process_q = asyncio.Queue()
        # schedules a task to consume all dispatchables, as they come
        cls.running_workers["processor"] = asyncio.create_task(
            cls.start_polling_process())
        # schedules a task to consume all and only the 'schedulable' dispatchables,
        # typically calendar notifications, at a  set interval. 1 minute looks OK.
        cls.running_workers["clock"] = asyncio.create_task(
            cls.start_ticking_clock(seconds))

    @classmethod
    def stop(cls) -> None:
        for t in cls.running_workers.values():
            t.cancel()

    @classmethod
    async def put(cls, dispatchable: Union[Dispatchable, Dict[str, Any]]) -> None:
        """ 
        Ensures that the input is a unique dispatchable and puts it into the queue.
        Performance may favor a different way of unpacking the inner dispatchable.
        """
        item = HashedDispatchable(
            **dispatchable.dict()
        ).dict() if isinstance(dispatchable, Dispatchable) else dispatchable
        if not "id" in item:
            raise Exception("Cannot process items without id!")
        await cls.process_q.put(item)

    @classmethod
    async def start_polling_process(cls) -> None:
        """
        Dispatches the item just in case it is not a scheduled item. Otherwise 
        adds to the scheduled items, if its id is not already keyed in the scheduled dict.
        """
        LOGGER.info("Started to poll the process queue.")
        while True:
            item = await cls.process_q.get()
            if not item["schedules"]:
                await cls.dispatch(item)
            elif not item["id"] in cls.scheduled:
                cls.scheduled[item["id"]] = item
            cls.process_q.task_done()

    @classmethod
    async def start_ticking_clock(cls, interval: int) -> None:
        """ 
        Every {interval}, monitor the scheduled set for due items.
        Looks for the last 'schedule' occurrence (i.e. a particular notification 
        and dispatches it. Notice that this behaviour assumes that the interval between 'schedules'
        is not smaller than the interval of 'start_ticking_clock'.
        """
        LOGGER.info("Started to monitor scheduled items")
        while True:
            await asyncio.sleep(interval)
            now_timestamp = datetime.now().timestamp()
            due = [v for v in cls.scheduled.values() if v["schedules"]
                   [-1] < now_timestamp]
            if due:
                await wait_for(cls.dispatch(due), timeout=3)

    @classmethod
    async def unschedule(cls, item_id: str) -> None:
        """ Unschedule (marks for cancellation) a scheduled items. """
        found = [k for k in cls.scheduled.keys() if k == item_id]
        if found:
            await as_async(cls.unscheduled_items_ids.add)(item_id)

    @classmethod
    async def dispatch(cls, items: List[Dict[str, Any]]) -> None:
        """
        The dispatcher looks up the 'unscheduled' set, to see if the item being processed is found there. 
        If found, the item is removed from the set and discarded. 
        If not found, the item is has its notification payload either added to a queue available for external applications to poll, or tried for push/sending.
        If the push/sending fails, the item is sent to the queue again unless it has been retried 3 times already (discarded if so). 
        If the sending succeeds, the item is rescheduled if it has remaining scheduled times. Otherwise it is removed from the the scheduled items.
        """
        LOGGER.info(f"Called dispatch with {len(items)}")
        now_tmp = datetime.now().timestamp()
        to_push = []
        redis_jobs = []

        def deleting(id: int) -> None:
            cls.scheduled.__delitem__(id)
            #LOGGER.info(f"Deleting {id}")

        def removing(id: int) -> None:
            cls.unscheduled_items_ids.remove(id)
            deleting(id)
            #LOGGER.info(f"Removing {id}")

        def polling(item: Dict[str, Any]) -> None:
            item["notification"]["dispatched"] = now_tmp
            cls.due_for_polling_notifications.appendleft(item)
            #LOGGER.info(f"Polling {item}")

        def rescheduling(item: Dict[str, Any]) -> None:
            cls.scheduled[item["id"]] = item
            #LOGGER.info(f"Scheduling {item}")

        for i in items:
            if i["id"] in cls.unscheduled_items_ids:
                redis_jobs.append(lambda: removing(i["id"]))
                #LOGGER.info(f"To remove {i['id']}")

            if i["notification"]["poll_do_not_push"]:
                redis_jobs.append(lambda: polling(i))
                #LOGGER.info(f"To poll {i}")

            else:
                to_push.append(cls.push(i))
                #LOGGER.info(f"To push {i}")

            if i["schedules"]:
                i["schedules"].pop()
            if not i["schedules"]:
                redis_jobs.append(lambda: deleting(i["id"]))
                #LOGGER.info(f"To delete {i['id']}")

            else:
                redis_jobs.append(lambda: rescheduling(i))

        for res in asyncio.as_completed(to_push):
            response = await res
            i = response["item"]
            if cls.has_toretry(response):
                LOGGER.warning(f"item sending timed out. Retrying soon.")
                i["retries"] += 1
                await cls.put(i)
            else:
                LOGGER.warning(
                    f"Dropping notification {i['notification']} after 3 unsuccessful retries: {i}")

        await as_async(run_redis_jobs)(redis_jobs)

    @classmethod
    async def poll_due(cls, sync: bool) -> List[Dict[Any, str]]:
        """ 
        Exposes all due schedulables for pollings. When 'sync' is true, performs a destructive sync in the sense that
        all polled items are deleted forever. Else the due schedulables are polled and stay there.
        """
        if not sync or not cls.due_last_poll:
            return list(cls.due_for_polling_notifications)

        def drop_condition(
            item): return item["notification"]["dispatched"] < cls.due_last_poll
        def take_condition(
            item): return item["notification"]["dispatched"] > cls.due_last_poll
        slice = list(dropwhile_takeif(
            cls.due_for_polling_notifications, drop_condition, take_condition))
        redis_jobs = [cls.due_for_polling_notifications.pop for _ in slice]
        await as_async(run_redis_jobs)(redis_jobs)
        cls.due_last_poll = datetime.now().timestamp()
        return slice

    @staticmethod
    async def push(item: Dict[str, Any], testing: bool = True) -> Dict[str, Any]:
        """ Sends a dispatched dispatchable to its final destination. """
        if not testing:
            if data := item["requests_options"]["data"]:
                async with Req(item["requests_options"]["url"], json=data) as response:
                    return {"status": response.status, "item": item}
        return {"status_code": 200, "item": item}

    @staticmethod
    def has_toretry(response: Dict[str, Any]):
        return response["status_code"] != 200 and response["item"]["retries"] < 3


@app.get(f"/{__MODULE_NAME__}/poll_due/")
async def poll_due(sync: Optional[bool] = None) -> QueryResponse:
    query = Query(service=__MODULE_NAME__)
    results = await Dispatcher.poll_due(True if sync is None else sync)
    return QueryResponse(query=query, results_count=len(results), results=results)
