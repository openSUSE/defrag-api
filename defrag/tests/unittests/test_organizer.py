import asyncio
from datetime import datetime, timedelta
from defrag.modules.db.redis import RedisPool
from itertools import count
from random import randint
from typing import Any, Generator, Optional
from defrag.modules.dispatcher import EmailNotification, Dispatcher
from defrag.modules.organizer import Calendar, CustomEvent, FedocalEvent, Reminders, FORMAT, Rrule
from defrag.routes.organizer import get_calendar, cancel_event, add_events, add_reminders, add_fedocal_events, add_reminders_for
from defrag.modules.organizer import Reminders
import pytest


def reminders_factory(with_tgt: Optional[bool] = False) -> Generator[Reminders, Any, Any]:
    for n in count(start=0, step=1):
        notification = EmailNotification(
            body="The body is the mind of communication",
            poll_do_not_push=False, email_address="email address",
            email_object="email object")
        deltas = Reminders.UserDeltas(weeks=1)
        yield Reminders(
            tgt=(timedelta(days=n) + datetime.now()).strftime(FORMAT),
            notification=notification, deltas=deltas) if with_tgt else Reminders(notification=notification,
                                                                                 deltas=deltas
                                                                                 )


def meetings_factory() -> Generator[CustomEvent, Any, Any]:
    for n in count(start=0, step=1):
        yield CustomEvent(
            id=randint(1, 10000),
            title="some title",
            manager="manager name",
            creator="creator name",
            created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            start=f"2021-10-1{n} 08:00:00",
            end=f"2021-10-1{n+1} 09:00:00",
            description="some description",
            location="openSUSE jitsi meet",
            tags=["defrag", "onboarding", "knowledge transfer"],
            restricted=[],
            rrule=Rrule(freq="weekly", until="2021-12-31 08:00:00")
        )


def fedocal_meetings_factory() -> Generator[FedocalEvent, Any, Any]:
    for n in count(start=1, step=1):
        yield FedocalEvent(
            event_id=randint(1, 10000),
            event_name="name",
            event_manager="manager",
            event_date=f"2021-10-1{n}",
            event_date_end=f"2021-10-1{n+1}",
            event_time_start="08:00:00",
            event_time_stop="09:00:00",
            event_timezone="utc",
            event_information="some event information",
            event_location="openSUSE jitsi meet",
            calendar_name="openSUSE community calendar",
        )

@pytest.mark.asyncio
async def test_reminders():
    with RedisPool() as conn:
        conn.flushall()
    Calendar.viewer = {}
    Dispatcher.run(60)
    item = next(reminders_factory())
    item.tgt = datetime.now().strftime(FORMAT)
    response = await add_reminders(item)
    await asyncio.sleep(1)
    assert response
    assert len(Dispatcher.scheduled) == 1
    Dispatcher.stop()


@pytest.mark.asyncio
async def test_add_fedocal_meetings():
    with RedisPool() as conn:
        conn.flushall()
    Calendar.viewer = {}
    Dispatcher.run(60)
    meetings_f, reminders_f = fedocal_meetings_factory(), reminders_factory()
    meetings = [next(meetings_f) for _ in range(0, 3)]
    reminders = next(reminders_f)
    response = await add_fedocal_events(meetings, reminders)
    await asyncio.sleep(1)
    assert response
    assert len(Dispatcher.scheduled) == 3
    Dispatcher.stop()


@pytest.mark.asyncio
async def test_add_meetings():
    with RedisPool() as conn:
        conn.flushall()
    Calendar.viewer = {}
    Dispatcher.run(60)
    meetings_f, reminders_f = meetings_factory(), reminders_factory()
    meetings = [next(meetings_f) for _ in range(0, 3)]
    reminders = next(reminders_f)
    response = await add_events(meetings, reminders)
    assert response
    assert len(Dispatcher.scheduled) == 3
    Dispatcher.stop()


@pytest.mark.asyncio
async def test_cancel_meeting():
    with RedisPool() as conn:
        conn.flushall()
    Calendar.viewer = {}
    Dispatcher.run(60)
    meetings_f, reminders_f = meetings_factory(), reminders_factory()
    meetings = [next(meetings_f) for _ in range(0, 3)]
    reminders = next(reminders_f)
    response = await add_events(meetings, reminders)
    print(response)
    cancellable_id = response.results[randint(0, 2)]
    response = await cancel_event(cancellable_id)
    start, end = "2021-10-10 08:00:00", "2021-12-30 00:00:00"
    res = await get_calendar(start, end)
    Dispatcher.stop()
    assert res.results_count == 2

@pytest.mark.asyncio
async def test_get_calendar():
    with RedisPool() as conn:
        conn.flushall()
    Calendar.viewer = {}
    Dispatcher.run(60)
    meetings_f, reminders_f = meetings_factory(), reminders_factory()
    meetings = [next(meetings_f) for _ in range(0, 3)]
    reminders = next(reminders_f)
    res = await add_events(meetings, reminders)
    start, end = "2021-10-10 08:00:00", "2021-12-30 00:00:00"
    res = await get_calendar(start, end)
    print(f"The calendar currently holds {res.results_count} items.")
    Dispatcher.stop()
    assert res.results_count == 3

@pytest.mark.asyncio
async def test_set_reminders_for():
    with RedisPool() as conn:
        conn.flushall()
    Calendar.viewer = {}
    Dispatcher.run(60)
    meeting = next(meetings_factory())
    reminders = next(reminders_factory())
    response = await add_events([meeting], reminders)
    event_id = response.results[0]
    res = await add_reminders_for(event_id, reminders)
    print(f"Results: {res}")
    await asyncio.sleep(1)
    print(f"Dispatched: {Dispatcher.scheduled}")
    assert len(list(Dispatcher.scheduled)) == 2
    Dispatcher.stop()