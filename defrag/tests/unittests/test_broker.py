from defrag.modules.db.redis import RedisPool
import pytest
from defrag.modules.helpers.broker import MessagesBroker, Message
import asyncio
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_broker():
    with RedisPool() as connection:
        connection.flushall()
    asyncio.create_task(MessagesBroker.run())
    # For good measure let's sleep to be sure everything is set up.
    await asyncio.sleep(1)
    now = datetime.now()
    tmp_now = now.timestamp()
    message1 = Message(
        message_id=1,
        timestamp=tmp_now,
        sender="Adrien",
        addressee="Jens",
        text="Hope we get a third"
    ).dict()
    message2 = Message(
        message_id=2,
        timestamp=tmp_now,
        sender="Adrien",
        addressee="Jens",
        text="programmer soon!",
        scheduled=(now + timedelta(seconds=3)).timestamp()
    ).dict()
    await MessagesBroker.put(message1)
    await MessagesBroker.put(message2)
    await asyncio.sleep(5)
    assert MessagesBroker.process_q.empty()
    assert len(MessagesBroker.scheduled) == 0
