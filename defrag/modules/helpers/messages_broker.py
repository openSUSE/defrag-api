from dataclasses import dataclass
from defrag import pretty_log
from defrag.modules.db.redis import RedisPool
from pottery import RedisDeque
from typing import Any, Dict, Generator, Optional
import asyncio


@dataclass
class Message:
    timestamp: float
    sender: str
    addressee: str
    text: str
    retries: Optional[int]

    def to_dict(self) -> Dict[Any, Any]:
        return vars(self)


class MessagesBroker:
    """
    Two queues are polled. Whenever a message on the high priority queue has
    its sending time out, it is put to the low priority queue. The low priority
    queue is polled only after the entire high priority queue has been consumed.
    """

    high_q = RedisDeque([], redis=RedisPool().connection, key="broker_high_q", maxlen=1000)
    low_q = RedisDeque([], redis=RedisPool().connection, key="broker_low_q", maxlen=1000)

    @classmethod
    def put(cls, message: Dict[Any, Any]) -> None:
        try:
            cls.high_q.appendleft(message)
        except Exception as error:
            print(f"Error when pushing {error}")

    @classmethod
    def from_queues(cls) -> Generator[Dict[Any, Any], None, None]:
        while cls.high_q:
            message = cls.high_q.pop()
            yield message
        while cls.low_q:
            message = cls.low_q.pop()
            yield message

    @classmethod
    async def start_poll(cls) -> None:
        """ 'Worker' to drive the polling of both queues. """
        await asyncio.sleep(1)
        try:
            for message in cls.from_queues():
                await cls.dispatch(message)
        except Exception as error:
            print(f"Error while polling: {error}")
        finally:
            asyncio.create_task(cls.start_poll())

    @staticmethod
    async def dispatch(message: Dict[Any, Any]) -> None:
        response = await MessagesBroker.send(message)
        if response["status_code"] == 200:
            print(f"Thanks for this message {message}")
        else:
            print(f"Message sending timed out. Retrying soon.")
            MessagesBroker.low_q.appendleft(message)

    @staticmethod
    async def send(message: Dict[Any, Any]) -> Dict[str, int]:
        pretty_log("Faking message sending...", "")
        await asyncio.sleep(1)
        return {"status_code": 200}
