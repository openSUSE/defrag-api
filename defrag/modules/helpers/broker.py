
from asyncio.tasks import wait_for
from datetime import date, datetime, timedelta
from defrag import LOGGER
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.data_manipulation import find_first
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers.requests import Req
from pottery import RedisDeque, RedisSet
from pydantic import BaseModel
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import asyncio


class ReqOpts(BaseModel):
    url: str
    settings: Optional[Dict[str, Any]]
    data: Optional[Any]


class RawMessage(BaseModel):
    sender: str
    addressee: str
    text: str
    reqopts: Optional[ReqOpts] = None
    scheduled: Optional[float] = None


class Message(RawMessage):
    message_id: int
    timestamp: float
    retries: int = 0


class MessagesBroker:
    """
    - Clients can subscribe as pushees, pollers, or both (to implement).
    - Pushees should be ready to handle HTTP requests. Pollers are not required to be so.
    - Single queue.
    - Whenever a message on the queue has its handler time out, it is cached to the `scheduled` set.

    TODO:
    - Add functionality for subscribing clients.
    - Add confirmation for all new subscriptions, with the confirmation not being a response but a
    call back testing the pushee's endpoint.
    """

    process_q: asyncio.Queue
    scheduled = RedisSet([], redis=RedisPool().connection,
                         key="broker_scheduled")
    unscheduled_messages_ids = RedisSet(
        [], redis=RedisPool().connection, key="broker_unscheduled")
    subscribed_pushees = RedisSet(
        [], redis=RedisPool().connection, key="broker_subscribed_pushees")
    subscribed_pollers = RedisSet(
        [], redis=RedisPool().connection, key="broker_subscribed_pollers")

    test_output = []

    @staticmethod
    def prime_message(raw: RawMessage) -> Message:
        if not isinstance(raw, RawMessage):
            raise Exception(f"Not a well-formed RawMessage: {str(raw)}")
        timestamp = datetime.now().timestamp()
        message_keyvals = {"timestamp": timestamp,
                           "message_id": hash(timestamp)}
        merged = {**raw.dict(), **message_keyvals}
        return Message(**merged)

    @classmethod
    async def run(cls) -> None:
        """ Installs an Event into the class and schedules the two data consumers. """
        cls.process_q = asyncio.Queue()
        asyncio.gather(cls.start_polling_process(), cls.start_ticking_clock())

    @classmethod
    async def put(cls, message: Dict[str, Any]) -> None:
        if message["scheduled"]:
            return cls.scheduled.add(message)
        cls.process_q.put_nowait(message)

    @classmethod
    async def start_polling_process(cls) -> None:
        LOGGER.info("Started to poll the process queue.")
        while True:
            message = await cls.process_q.get()
            await cls.dispatch(message)
            cls.process_q.task_done()

    @classmethod
    async def start_ticking_clock(cls, interval: int = 1) -> None:
        """ Every second, concurrently consumes the entire scheduled set. """
        LOGGER.info("Started to monitor scheduled messages")
        while True:
            await asyncio.sleep(interval)
            now_timestamp = datetime.now().timestamp()
            due: List[Dict[str, Any]] = [
                m for m in cls.scheduled if m["scheduled"] <= now_timestamp]
            await asyncio.gather(*[cls.dispatch(m) for m in due])

    @classmethod
    def unschedule(cls, message_id: int) -> None:
        found = [m for m in cls.scheduled if m["message_id"] == message_id]
        if found:
            cls.unscheduled_messages_ids.add(message_id)

    @classmethod
    async def dispatch(cls, message: Dict[str, Any]) -> None:
        """
        The dispatcher looks up the 'unscheduled' set, to see if the message
        being processed is found there. If found, the message is removed from the set
        and discarded. If not found, the message is dispatched to the 'send' function.
        Then if the send function fails, the message is rescheduled for delivery within the next 5 seconds.
        """
        if message["message_id"] in cls.unscheduled_messages_ids:
            cls.unscheduled_messages_ids.remove(message["message_id"])
        if message in cls.scheduled:
            cls.scheduled.remove(message)
        response = await cls.send(message)
        if response["status"] != 200:
            LOGGER.warning(f"Message sending timed out. Retrying soon.")
            message["retries"] += 1
            message["scheduled"] = (
                datetime.now() + timedelta(seconds=5)).timestamp()
            await cls.put(message)
        else:
            cls.test_output.append(message)

    @staticmethod
    async def send(message: Dict[str, Any], testing: bool = True) -> Any:
        if not testing:
            if data := message["requests_options"]["data"]:
                async with Req(message["requests_options"]["url"], json=data) as response:
                    return response
        LOGGER.info(f"Message sent! {str(message)} at {str(datetime.now())}")
        return {"status": 200}
