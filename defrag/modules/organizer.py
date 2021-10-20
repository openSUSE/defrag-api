import asyncio
from defrag.modules.helpers.data_manipulation import partition_left_right
from functools import reduce
from datetime import datetime, timedelta, timezone
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.db.redis import RedisPool
from defrag.modules.helpers import EitherErrorOrOk, FailuresAndSuccesses
from defrag.modules.dispatcher import Dispatcher, Dispatchable, Notification, TelegramNotification
from pottery import RedisDict
from typing import Any, Dict, List, Optional, Tuple
from dateutil import rrule
from pydantic.main import BaseModel
from defrag.modules.helpers.requests import Req

__MOD_NAME__ = "organizer"

CAL_NAME = "openSUSE Community Calendar"
FEDOCAL_URL = ""
POLL_INTERVAL = timedelta(days=15)
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

# ----
# DATA
# ----


class FedocalEvent(BaseModel):
    """ Meets the fedocal event specs as per 
    https://github.com/fedora-infra/fedocal/blob/master/fedocal/api.py
    """
    event_id: int
    event_name: str
    event_manager: str
    event_date: str
    event_date_end: str
    event_time_start: str
    event_time_stop: str
    event_timezone: str
    event_information: str
    event_location: str
    calendar_name: str


class Rrule(BaseModel):
    """
    This class is meant as a support class for CustomEvent.
    In particular, if 'dtstart' is not set at initialization,
    the program's business logic will fallback on to the 'start' field
    declared on the CustomEvent instance the Rrule instance defined in the CustomEvent instance.
    Look at https://dateutil.readthedocs.io/en/stable/rrule.html for reference about the 'rrule' language.
    """
    until: str  # date str as FORMAT-ed above
    freq: str
    dtstart: Optional[str] = None   # date str as FORMAT-ed above
    interval: Optional[int] = None

    # TODO implement this:
    """
    wkst = None
    count = None
    bysetpos = None
    bymonth = None
    bymonthday = None
    byyearday = None
    byeaster = None
    byweekno = None
    byweekday = None
    byhour = None
    byminute = None
    bysecond = None
    cache = False
    """


class CustomEvent(BaseModel):

    id: str
    title: str
    manager: str # as datetime.strftime with "%Y-%m-%d%H:%M:%S" from datetime.now(timezone.utc)
    creator: str
    start: str  # as datetime.strftime with "%Y-%m-%d%H:%M:%S" from target UTC datetime
    end: str    # as datetime.strftime with "%Y-%m-%d%H:%M:%S" from target UTC datetime
    description: str
    location: str
    status: Optional[str]
    tags: Optional[List[str]] = None
    restricted: Optional[List[str]] = None
    rrule: Optional[Rrule] = None
    rruled_occurrences: Optional[List[str]] = None
    changelog: Optional[List[Dict[str, Any]]] = None

    def apply_rrule(self) -> List[str]:
        if not self.rrule:
            raise Exception(
                f"Tried applied the instance's rrule, which is not defined yet.")
        rule = None
        freq = None
        until = datetime.strptime(self.rrule.until, FORMAT)
        dtstart = datetime.strptime(
            self.rrule.dtstart, FORMAT) if self.rrule.dtstart else datetime.strptime(self.start, FORMAT)
        if self.rrule.freq.upper() == "DAILY":
            freq = rrule.DAILY
        if self.rrule.freq.upper() == "WEEKLY":
            freq = rrule.WEEKLY
        if self.rrule.freq.upper() == "MONTHLY":
            freq = rrule.MONTHLY
        if self.rrule.interval:
            rule = {"until": until, "freq": freq, "dtstart": dtstart,
                    "interval": self.rrule.interval}
        else:
            rule = {"until": until, "freq": freq, "dtstart": dtstart}
        occurrences = rrule.rrule(**rule)
        return list(map(lambda d: datetime.strftime(d, FORMAT), occurrences))


# ---------
# UTILITIES
# ---------


def disassemble_to_date_time(d: datetime) -> Tuple[str, str]:
    date = d.strftime(DATE_FORMAT)
    time = d.strftime(TIME_FORMAT)
    return date, time


def assemble_to_datetime(d: str, t: str) -> datetime:
    return datetime.strptime(f"{d} {t}", FORMAT)


def event_from_fedocal(m: FedocalEvent) -> CustomEvent:
    start = assemble_to_datetime(
        m.event_date, m.event_time_start).strftime(FORMAT)
    end = assemble_to_datetime(
        m.event_date_end, m.event_time_stop).strftime(FORMAT)
    return CustomEvent(
        id=m.event_id,
        title=m.event_name,
        manager=m.event_manager,
        creator=CAL_NAME,
        created=datetime.now(timezone.utc).strftime(FORMAT),
        start=start,
        end=end,
        description=m.event_information,
        location=m.event_information,
        tags=[],
        restricted=[],
        rrule=None,
        status="active"
    )


def event_to_fedocal(m: CustomEvent) -> FedocalEvent:
    date, time_start = disassemble_to_date_time(
        datetime.strptime(m.start, FORMAT))
    date_end, time_stop = disassemble_to_date_time(
        datetime.strptime(m.end, FORMAT))
    return FedocalEvent(
        event_id=m.id,
        event_name=m.title,
        event_manager=m.manager,
        event_date=date,
        event_date_end=date_end,
        event_time_start=time_start,
        event_time_stop=time_stop,
        event_time_zone="utc",
        event_information=m.description,
        event_location=m.location,
        calendar_name=CAL_NAME
    )


# ---------
# REMINDERS
# ---------

class Reminders(BaseModel):
    """
    Instances of this class are supposed to be passed along with instances of CustomEvent
    to specificy the notification behaviour expected by the user registering the event.
    This makes sense for community events with a dedicated news channel, but it does not make sense
        - (TODO) for users interested to have their own notifications about an event that already exits (as well as its (re)occurrences)
        - for users users interested to have their own notifications independently of any calendar items (these are expected 
            to set their own reminders using the 'set_reminders' endpoint. The function creates reminders independently of any event.
    """

    class UserDeltas(BaseModel):
        weeks: Optional[int]
        days: Optional[int]
        hours: Optional[int]
        minutes: Optional[int]

        def apply(self, tgt: str) -> List[float]:
            deltas = []
            dtgt = datetime.strptime(tgt, FORMAT)
            if self.weeks:
                deltas.append((dtgt - timedelta(weeks=self.weeks)).timestamp())
            if self.days:
                deltas.append((dtgt - timedelta(days=self.days)).timestamp())
            if self.hours:
                deltas.append((dtgt - timedelta(hours=self.hours)).timestamp())
            if self.minutes:
                deltas.append(
                    (dtgt - timedelta(hours=self.minutes)).timestamp())
            return deltas

    notification: Notification
    deltas: UserDeltas
    tgt: Optional[str]  # date string using the usual format defined above

    @staticmethod
    async def schedule(tgt: str, notification: Notification, deltas: UserDeltas) -> None:
        await Dispatcher.put(Dispatchable(origin="reminders", schedules=deltas.apply(tgt), notification=notification))


# --------
# CALENDAR
# --------


class Calendar:

    # holds the actual calendar items
    container = RedisDict({}, redis=RedisPool().connection,
                          key=CAL_NAME)
    # maps str hashes into datetimes for quicker access
    viewer: Dict[str, datetime] = {}

    @classmethod
    async def add(cls, _event: CustomEvent, notification: Notification, deltas: Reminders.UserDeltas) -> EitherErrorOrOk:
        """ Adds an item to the calendar, computes it's occurrences, schedules the notification messages as reminders. """
        
        # setup
        event, at = cls.prime_event(_event), datetime.strptime(_event.start, FORMAT)

        # errors handling
        if not cls.viewer:
            # need to populate the viewer
            cls.viewer = {m['id']: datetime.strptime(m['start'], FORMAT) for m in cls.container}
        if event.id in cls.viewer:
            return EitherErrorOrOk(error=f"Unable to add this event as it was added already: {str(event)}")        
        
        # occurrences and dispatchable
        future_occurrences = event.apply_rrule() if event.rrule else [event.start]
        schedules: List[float] = reduce(lambda acc, o: acc + deltas.apply(o), future_occurrences, [])
        disp = Dispatchable(
            origin=CAL_NAME,
            notification=notification,
            id=event.id,
            schedules=schedules
        )
        
        def inserting(event_id: str) -> None:
            event.status = "active"
            event.rruled_occurrences = future_occurrences
            cls.container[event_id] = event.dict()
        
        # scheduling notifications and running redis job, then updating the viewer
        await asyncio.gather(Dispatcher.put(disp), as_async(inserting)(event.id))
        cls.viewer[event.id] = at

        # we're returning this so that the caller / user knows which ids have been used.
        # required for cancellation.
        return EitherErrorOrOk(ok={"id": event.id, "title": event.title, "start": event.start, "end": event.end})

    @classmethod
    async def cancel(cls, event_id: str) -> EitherErrorOrOk:
        """ Removes an item from the calendar, to implement the 'cancellation' behaviour expected by the user. """
        
        if not event_id in cls.viewer:
            return EitherErrorOrOk(error=f"Unable to cancel any event with id {event_id} as it matches not event in cache")

        # work for redis
        def cancelling(key: str) -> None:
            item = cls.container[key]
            status = "cancelled"
            item["status"] = status
            item["changelog"].append({"action": status, "at": datetime.now().strftime(FORMAT)})
            cls.container[key] = item

        # running jobs, cancelling notifications
        await asyncio.gather(Dispatcher.unschedule(event_id), as_async(cancelling)(event_id))
        return EitherErrorOrOk(ok=event_id)

    @classmethod
    async def add_all_new_events(
        cls,
        notification: Notification,
        deltas: Reminders.UserDeltas,
        events: Optional[List[CustomEvent]]
    ) -> FailuresAndSuccesses:
        """ Adds many events using a single notification behaviour. Expected for community affairs. """
        
        to_add = events or []
        
        if not to_add:
            # fetching from the fedocal endpoint
            fedocal_events = await cls.poll_fedocal()
            to_add = [event_from_fedocal(m) for m in fedocal_events if m.event_id not in cls.container.keys()]
        
        results = await asyncio.gather(*[cls.add(m, notification, deltas) for m in to_add])
        return FailuresAndSuccesses(*partition_left_right(results, lambda item: hasattr(item, "ok")))

    @staticmethod
    async def poll_fedocal(interval=None) -> List[FedocalEvent]:
        """
        For a given fedocal API endpoints, returns all the items found there between now and 
        the set interval.
        """
        now = datetime.now()
        start, _ = disassemble_to_date_time(datetime.now())
        end, _ = disassemble_to_date_time(now + (interval or POLL_INTERVAL))
        async with Req(FEDOCAL_URL, params={"start": start, "end": end}) as response:
            res = await response.json()
            return [FedocalEvent(**entry) for entry in res["events"]]

    @staticmethod
    async def set_reminders_from_fedocal(events: List[FedocalEvent], user_deltas: Reminders.UserDeltas) -> EitherErrorOrOk:
        """
        Schedules reminders corresponding to a list of fedocal events.
        """
        to_schedule = [Dispatchable(id=m.event_id, origin="openSUSE_fedocal", schedules=user_deltas.apply(
            f"{m.event_date} {m.event_time_start}"), notification=TelegramNotification(body=m.event_information)) for m in events]
        await asyncio.gather(*[Dispatcher.put(m) for m in to_schedule])
        return EitherErrorOrOk(ok="Reminders set!")

    @staticmethod
    def prime_event(event: CustomEvent) -> CustomEvent:
        event.id = str(abs(hash(event.creator + event.start + event.end)))
        event.changelog = [{"created": datetime.now().strftime(FORMAT)}]
        return event

    @staticmethod
    async def render(start_str: str, end_str: str, also_cancelled: bool = False) -> List[Dict[str, Any]]:
        """
        Returns a view of the calendar in the specified range encoded in the date strings arguments.
        """
        if not Calendar.container:
            return []
        
        start, end = datetime.strptime(start_str, FORMAT), datetime.strptime(end_str, FORMAT)
        
        after = [
            k for k, v in Calendar.viewer.items()
            if start <= v and v <= end
        ]

        condition = (lambda item: item["id"] in after) if also_cancelled else (
            lambda item: item["id"] in after and item["status"] != "cancelled")

        def rendering() -> List[Dict[str, Any]]:
            return [e for e in Calendar.container.values() if condition(e)]
        return await as_async(rendering)()
