from asyncio.tasks import as_completed
from datetime import datetime, timedelta
from asyncio.locks import Event
from defrag import LOGGER
from defrag.modules.helpers.sync_utils import as_async, iterate_off_thread
from defrag.modules.helpers.data_manipulation import find_first
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.requests import Req
from pottery import RedisDeque, RedisSet
from pydantic import BaseModel
from typing import Any, AsyncGenerator, Dict, List, Optional
import asyncio


class ReqOpts(BaseModel):
    url: str
    settings: Optional[Dict[str, Any]]
    data: Optional[Any]


class Message(BaseModel):
    # We should add a random number generator to generate message_id
    message_id: int
    timestamp: float
    sender: str
    addressee: str
    text: str
    retries: int = 0
    reqopts: Optional[ReqOpts] = None
    scheduled: Optional[float] = None


class MessagesBroker:
    """
    - Clients can subscribe as pushees, pollers, or both (to implement).
    - Pushees should be ready to handle HTTP requests. Pollers are not required to be so.
    - Two queues are polled in parallel; `scheduled_q` is fed all messages with a truthy 'scheduled' field,
        while `process_q` is fed all the others. They process their messages concurrently, however.
    - Both queues pollers have built-in sychronization mechanisms. They should run forever, and never block the
        event loop.
    - Whenever a message on the process queue has its handler time out, it is put to scheduled queue.

    TODO:
    - Add functionality for subscribings clients.
    - Add confirmation for all new subscriptions, with the confirmation not being a response but a
    call back testing the pushee's endpoint.
    - Generate ids with a proper generator.
    """

    ready_to_process: Event
    process_q = RedisDeque([], redis=RedisPool().connection,
                           key="broker_process_q", maxlen=1000)
    scheduled_q = RedisDeque([], redis=RedisPool().connection,
                             key="broker_scheduled_q", maxlen=1000)
    unscheduled = RedisSet(
        [], redis=RedisPool().connection, key="broker_unscheduled")
    subscribed_pushees = RedisSet(
        [], redis=RedisPool().connection, key="broker_subscribed_pushees")
    subscribed_pollers = RedisSet(
        [], redis=RedisPool().connection, key="broker_subscribed_pollers")

    @classmethod
    async def run(cls):
        """ Installs an Event into the class and schedules the two queue consumers. """
        cls.ready_to_process = asyncio.Event()
        asyncio.gather(*[cls.start_polling_process(),
                       cls.start_polling_scheduled()])

    @classmethod
    async def put(cls, message: Dict[str, Any]) -> None:
        """
        Puts a message into the corresponding queue ('scheduled' if this field is found in the message,
        the other queue otherwise), and then notifies the holder of the event,
        `start_poll`, that the process_q is available for polling.
        """
        try:
            if message["scheduled"]:
                return await cls.schedule(message)
            await as_async(cls.process_q.appendleft)(message)
            if not cls.ready_to_process.is_set():
                cls.ready_to_process.set()
        except Exception as error:
            LOGGER.error(f"Error when putting: {error}")

    @classmethod
    async def start_polling_process(cls):
        """
        - wait until the Event notifies this function that the process_q is non-empty; and
        - iterates over the class' async generator, acquiring coroutines results in sequence; and finally
        - re-schedules itself.
        """
        await cls.ready_to_process.wait()
        async for message in cls.pop_process_q():
            await cls.dispatch(message)
        cls.ready_to_process.clear()
        asyncio.create_task(cls.start_polling_process())

    @classmethod
    async def start_polling_scheduled(cls, interval: int = 1):
        """
        Every second, concurrently consumes the entire scheduled_q, and
        reschedules itself.
        """
        await asyncio.sleep(interval)
        timestamp = datetime.now().timestamp()
        # instead of producing coroutines as we consume the queue, better send the entire queue to a worker thread and 
        # consume only the returned results in a single batch
        messages: List[Dict[str, Any]] = await iterate_off_thread(cls.scheduled_q.pop, [m for m in cls.scheduled_q if m["scheduled"] <= timestamp])
        await asyncio.gather(*[cls.dispatch(m) for m in messages])
        asyncio.create_task(cls.start_polling_scheduled())

    @classmethod
    async def schedule(cls, message: Dict[str, Any]) -> None:
        """ Inserts a given message into the scheduled queue respecting ascending temporal order. """
        def relation(
            inserted: Dict[str, Any], to_insert: Dict[str, Any]) -> bool: return to_insert["scheduled"] < inserted["scheduled"]
        index = find_first(cls.scheduled_q, relation, message)
        await as_async(cls.scheduled_q.insert)(index, message)

    @ classmethod
    def unschedule(cls, message_id: int) -> None:
        """
        RedisDeque does not expose any interface for deleting on keys
        So instead we look for the first message with the same `message_id`, and if found,
        add its message_id to the 'to remove' set.
        """
        def relation(item: Dict[str, Any], message_id: int) -> bool:
            return item["message_id"] == message_id
        try:
            if find_first(cls.scheduled_q, relation, message_id) == -1:
                raise Exception(
                    f"There is no scheduled message ith this id: {str(message_id)}")
            cls.unscheduled.add(message_id)
        except Exception as error:
            LOGGER.error(
                f"Error while cancelled message {str(message_id)}: {error}")

    @ classmethod
    async def dispatch(cls, message: Dict[str, Any]) -> None:
        """
        The dispatcher looks up the 'unscheduled' set, to see if the message
        being processed is found there. If found, the message is removed from the set
        and discarded. If not found, the message is dispatched to the 'send' function.
        Then if the send function fails, the message is rescheduled for delivery within the next 5 seconds.
        """
        if message["message_id"] in cls.unscheduled:
            cls.unscheduled.remove(message["message_id"])
            return
        response = await cls.send(message)
        if response["status"] != 200:
            LOGGER.warning(f"Message sending timed out. Retrying soon.")
            message["retries"] += 1
            message["scheduled"] = (
                datetime.now() + timedelta(seconds=5)).timestamp()
            await cls.put(message)

    @staticmethod
    async def pop_process_q() -> AsyncGenerator[Dict[str, Any], None]:
        """ Tried with `asyncio.as_completed` instead but it was too slow. """
        for _ in MessagesBroker.process_q:
            yield await as_async(MessagesBroker.process_q.pop)()

    @staticmethod
    async def send(message: Dict[str, Any], testing: bool = True) -> Any:
        if not testing:
            if data := message["requests_options"]["data"]:
                async with Req(message["requests_options"]["url"], json=data) as response:
                    return response
        LOGGER.info(f"Message sent! {str(message)} at {str(datetime.now())}")
        return {"status": 200}
