from defrag.modules.db.redis import RedisPool
from defrag import app
from defrag.modules.helpers.dispatcher import Dispatcher, Dispatchable, EmailNotification, HashedDispatchable
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import pytest
import asyncio

client = TestClient(app)


@pytest.mark.asyncio
async def test_Dispatcher():
    with RedisPool() as conn:
        conn.flushall()
    now = datetime.now()
    notification = EmailNotification(
        poll_do_not_push=True, body="some contents", email_address="to someone", email_object="about something")
    schedules = [(now + timedelta(seconds=n)).timestamp() for n in range(3)]
    dispatchables = [Dispatchable(origin="test client", notification=notification, schedules=[s]) for s in schedules]
    
    Dispatcher.run(dry_run=True)
    
    for d in dispatchables:
        Dispatcher.put(d)
    
    await asyncio.sleep(6)
    
    print(
        f"Scheduled: {len(Dispatcher.scheduled)}, Available for polling: {len(Dispatcher.due_for_polling_notifications)}")
    
    assert len(Dispatcher.due_for_polling_notifications) == len(
        Dispatcher.scheduled) == 3


@pytest.mark.asyncio
async def test_poll_due():
    with RedisPool() as conn:
        conn.flushall()
    yesterday = (datetime.now() - timedelta(days=1)).timestamp()
    notifiers = [
        HashedDispatchable(
            Dispatchable(
                origin="test", notification=EmailNotification(
                poll_do_not_push=True,
                body="some contents",
                email_address="to someone",
                email_object="about something"
                )
            )
        ).__dict__() for _ in range(0, 10)
    ]
    
    for n in notifiers:
        n["dispatched"] = datetime.now().timestamp()
    
    Dispatcher.due_for_polling_notifications.extendleft(notifiers)
    Dispatcher.due_last_poll = yesterday
    
    polled = await Dispatcher.poll_due(True)
    assert len(polled) == len(notifiers)
