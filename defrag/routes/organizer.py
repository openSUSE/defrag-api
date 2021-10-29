from typing import List
from fastapi import APIRouter


from defrag.modules.helpers import QueryResponse, Query
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.organizer import CustomEvent, Reminders, Calendar, FORMAT, event_from_fedocal, FedocalEvent

router = APIRouter()


__ENDPOINT_NAME__ = "organizer"


@router.post("/" + __ENDPOINT_NAME__ +"/add_reminder/")
async def add_reminders(reminder: Reminders) -> QueryResponse:
    query = Query(service="organizer")
    if not reminder.tgt:
        return QueryResponse(query=query, error=f"You need to add a 'tgt' (datetime string encoded as {FORMAT} to set this reminder: {reminder}")
    await Reminders.schedule(tgt=reminder.tgt, notification=reminder.notification, deltas=reminder.deltas)
    return QueryResponse(query=Query(service="organizer"), message="Reminder(s) set!")


@router.post("/" + __ENDPOINT_NAME__ + "/add_reminder_for/")
async def add_reminders_for(event_id: int, reminders: Reminders) -> QueryResponse:
    query = Query(service="organizer")
    reply = "Calendar is empty!"
    if not Calendar.container:
        return QueryResponse(query=query, error=reply)

    def look_up(event_id):
        return Calendar.container[event_id] if event_id in Calendar.container.keys() else None
    found = await as_async(look_up)(event_id)
    if not found:
        reply = f"Unable to find this calendar item: {event_id}"
        return QueryResponse(query=query, error=reply)
    await Reminders.schedule(tgt=found["start"], notification=reminders.notification, deltas=reminders.deltas)
    return QueryResponse(query=query, message=f"Thanks, reminders set for {event_id}")


@router.post("/" + __ENDPOINT_NAME__ + "/add_fedocal_events/")
async def add_fedocal_events(events: List[FedocalEvent], reminders: Reminders) -> QueryResponse:
    query = Query(service="organizer")
    results = await Calendar.add_all_new_events(events=[event_from_fedocal(m) for m in events], notification=reminders.notification, deltas=reminders.deltas)
    keys = [e.ok["id"] for e in results.successes if hasattr(e, "ok")]
    return QueryResponse(query=query, message="event(s) added and reminder(s) set!", results=keys, results_count=len(keys))


@router.post("/" + __ENDPOINT_NAME__ + "/add_events/")
async def add_events(events: List[CustomEvent], reminders: Reminders) -> QueryResponse:
    query = Query(service="organizer")
    results = await Calendar.add_all_new_events(events=events, notification=reminders.notification, deltas=reminders.deltas)
    keys = [e.ok["id"] for e in results.successes if hasattr(e, "ok")]
    res = QueryResponse(query=query, message="event(s) added and reminder(s) set!",
                        results=keys, results_count=len(keys))
    return res


@router.post("/" + __ENDPOINT_NAME__ + "/cancel_event/")
async def cancel_event(event_id: str) -> QueryResponse:
    query = Query(service="organizer")
    result = await Calendar.cancel(event_id)
    if hasattr(result, "ok"):
        return QueryResponse(query=query, message=f"event and reminder(s) cancelled for {event_id}")
    else:
        return QueryResponse(query=query, message=f"Unable to cancel {event_id}")


@router.get("/" + __ENDPOINT_NAME__ + "/calendar/")
async def get_calendar(start: str, end: str) -> QueryResponse:
    query = Query(service="organizer")
    results = await Calendar.render(start_str=start, end_str=end)
    return QueryResponse(query=query, results=results, results_count=len(results))
