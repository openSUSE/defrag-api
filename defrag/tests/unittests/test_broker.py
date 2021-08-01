import pytest
from defrag.modules.helpers.messages_broker import MessagesBroker, Message
import asyncio
from datetime import datetime

@pytest.mark.asyncio
async def test_broker():
    asyncio.create_task(MessagesBroker.start_poll())
    message1 = Message(datetime.now().timestamp(),
                       "Adrien", "Jens", "Hope we get a third", 0)
    message2 = Message(datetime.now().timestamp(),
                       "Adrien", "Jens", "developer because you know, the more the better!", 0)
    MessagesBroker.put(message1.to_dict())
    MessagesBroker.put(message2.to_dict())
    await asyncio.sleep(5)
    assert len(MessagesBroker.high_q) + len(MessagesBroker.low_q) == 0
