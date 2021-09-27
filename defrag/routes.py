from defrag.modules.suggestions import Suggestions
from functools import partial
from typing import List, Optional
import asyncio

from defrag import app
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.dispatcher import Dispatcher
from defrag.modules.search import SearchQuery
from defrag.modules.twitter import search_tweets
from defrag.modules.helpers import CacheQuery, Query, QueryResponse
from defrag.modules.wikis import search_wikis_as_list
from defrag.modules.search import search_map
from defrag.modules.helpers.services_manager import Run
from defrag.modules.organizer import FORMAT, CustomEvent, FedocalEvent, Reminders, Calendar, event_from_fedocal
from defrag.modules.reddit import search_reddit
from defrag.modules.docs import get_data, make_leap_index, make_search_set_indexes_in_parallel, make_tumbleweed_index, ready_to_index, search_index, search_indexes_in_parallel, set_global_index, sorted_on_score, indexes
from defrag.modules.bugs import BugzillaQueryEntry, get_this_bug, search_all_bugs

modules = {}


def expose_modules_to_handlers(_modules: List[str]) -> None:
    global modules
    for m in _modules:
        modules[m] = m


""" Bugs """


@app.get("/" + modules['bugs'] + "/bug/{bug_id}")
async def get_bug(bug_id: int) -> QueryResponse:
    # declares how this request should interface with the cache
    cache_query = CacheQuery(service="bugs", item_key=bug_id)
    # declares what function to run if the item the request is looking for
    # cannot find it in the cache store
    fallback = partial(get_this_bug, bug_id)
    # run the request
    return await Run.query(cache_query, fallback)


@app.get("/" + modules['bugs'] + "/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[
                         {"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])


@app.get("/" + modules['bugs'] + "/search/")
async def search(term: str) -> QueryResponse:
    query = BugzillaQueryEntry(search_string=term)
    result = await search_all_bugs(query)
    # This is not as fancy as it was before, but now it actually works.
    # Plus, before id didn't cache anyway, so this should be fine. We can
    # still make it better in the future
    return QueryResponse(
        query=Query(
            service="bugs"),
        results_count=len(result),
        results=result)


""" Dispatcher """


@app.get(f"/{modules['dispatcher']}/poll_due/")
async def poll_due(sync: Optional[bool] = None) -> QueryResponse:
    query = Query(service=modules['dispatcher'])
    results = await Dispatcher.poll_due(True if sync is None else sync)
    return QueryResponse(query=query, results_count=len(results), results=results)


""" Docs """


@app.get("/" + modules['docs'] + "/single/{source}/")
async def search_single_source_docs(source: str, keywords: str) -> QueryResponse:
    if not ready_to_index([source]):
        if source == "tumbleweed":
            set_global_index("tumbleweed", make_tumbleweed_index(await get_data(source)))
        else:
            set_global_index("leap", make_leap_index(await get_data(source)))
    results = sorted_on_score(search_index(
        indexes[source]["index"], source, keywords))
    return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)


@app.get("/" + modules['docs'] + "/merged/")
async def handle_search_docs(keywords: str) -> QueryResponse:
    if not ready_to_index(["leap", "tumbleweed"]):
        results = await make_search_set_indexes_in_parallel(keywords)
        return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)
    else:
        results = sorted_on_score(search_indexes_in_parallel(keywords))
        return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)


""" Organizer """


@app.post(f"/{modules['organizer']}/add_reminder/")
async def handle_post_reminders(reminder: Reminders) -> QueryResponse:
    query = Query(service=modules['organizer'])
    if not reminder.tgt:
        return QueryResponse(query=query, error=f"You need to add a 'tgt' (datetime string encoded as {FORMAT} to set this reminder: {reminder}")
    await Reminders.schedule(tgt=reminder.tgt, notification=reminder.notification, deltas=reminder.deltas)
    return QueryResponse(query=Query(service=modules['organizer']), message="Reminder(s) set!")


@app.post(f"/{modules['organizer']}/add_reminder_for/")
async def handle_post_reminders_for(event_id: int, reminders: Reminders) -> QueryResponse:
    query = Query(service=modules['organizer'])
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


@app.post(f"/{modules['organizer']}/add_fedocal_events/")
async def handle_post_fedocal_events(events: List[FedocalEvent], reminders: Reminders) -> QueryResponse:
    query = Query(service=modules['organizer'])
    results = await Calendar.add_all_new_events(events=[event_from_fedocal(m) for m in events], notification=reminders.notification, deltas=reminders.deltas)
    keys = [e.ok["id"] for e in results.successes if hasattr(e, "ok")]
    return QueryResponse(query=query, message="event(s) added and reminder(s) set!", results=keys, results_count=len(keys))


@app.post(f"/{modules['organizer']}/add_events/")
async def handle_post_events(events: List[CustomEvent], reminders: Reminders) -> QueryResponse:
    query = Query(service=modules['organizer'])
    results = await Calendar.add_all_new_events(events=events, notification=reminders.notification, deltas=reminders.deltas)
    keys = [e.ok["id"] for e in results.successes if hasattr(e, "ok")]
    res = QueryResponse(query=query, message="event(s) added and reminder(s) set!",
                        results=keys, results_count=len(keys))
    return res


@app.post(f"/{modules['organizer']}/cancel_event/")
async def handle_post_cancel_event(event_id: str) -> QueryResponse:
    query = Query(service=modules['organizer'])
    result = await Calendar.cancel(event_id)
    if hasattr(result, "ok"):
        return QueryResponse(query=query, message=f"event and reminder(s) cancelled for {event_id}")
    else:
        return QueryResponse(query=query, message=f"Unable to cancel {event_id}")


@app.get(f"/{modules['organizer']}/calendar/")
async def handle_get_calendar(start: str, end: str) -> QueryResponse:
    query = Query(service=modules['organizer'])
    results = await Calendar.render(start_str=start, end_str=end)
    return QueryResponse(query=query, results=results, results_count=len(results))


""" Reddit """


@app.get("/" + modules['reddit'] + "/search/")
async def handle_search_reddit(keywords: str) -> QueryResponse:
    results = await search_reddit(keywords)
    query = Query(service=modules['reddit'])
    return QueryResponse(query=query, results=results, results_count=len(results))


@app.get(f"/{modules['reddit']}/")
async def get_reddit() -> QueryResponse:
    query = CacheQuery(service="reddit", item_key=None)
    return await Run.query(query, None)


""" Search (merged) """


@app.get(f"/{modules['search']}/")
async def handle_global_search(keywords: str, scope: str) -> QueryResponse:
    query = Query(service=modules['search'])
    sq = SearchQuery(keywords=keywords, scope=[
                     s.strip() for s in scope.split(",")])
    """
    TODO: the idea of making registered services a precondition for searching globally
    was that we would be using some cache. Not the case for now so dropping this precondition
    until we have a more intelligent solution.
    
    if missing_services := [s for s in sq.scope if not s in ServicesManager.services.list_enabled()]:
        error = f"You are trying to search from services that have not been enabled yet: {missing_services}"
        return QueryResponse(query=query, error=error)
    """
    searchers = [f for n, f in search_map.items() if n in sq.scope]
    results = {}
    results_counts = 0
    for response in asyncio.as_completed([search(sq.keywords) for search in searchers]):
        res = await response
        count = res.results_count
        results[res.query.service] = {
            "results": res.results, "results_count": count}
        results_counts += count
    return QueryResponse(query=query, results=results, results_count=results_counts)


""" Suggestions """


@app.get(f"/{modules['suggestions']}/")
async def get_suggestions(key: Optional[str] = None) -> QueryResponse:
    query = Query(service=modules['suggestions'])
    results = await Suggestions.view(key)
    if ok := results.is_ok():
        return QueryResponse(query=query, results=results, results_count=len(ok))
    return QueryResponse(query=query, error=str(ok))


@app.post(f"/{modules['suggestions']}/create/")
async def create_suggestion(sugg: Suggestions.New) -> QueryResponse:
    query = Query(service=modules['suggestions'])
    result = await Suggestions.add(sugg)
    if result.is_ok():
        return QueryResponse(query=query, message="Thanks!")
    return QueryResponse(query=query, error="Didn't turn out the way we anticipated!")


@app.post(f"/{modules['suggestions']}/vote_for_suggestion/")
async def vote_for_suggestion(voter_id: str, sugg_id: str, vote: int) -> QueryResponse:
    query = Query(service=modules['suggestions'])
    result = await Suggestions.cast_vote(voter_id=voter_id, key=sugg_id, vote=vote)
    if result.is_ok():
        return QueryResponse(query=query, message="Thanks!")
    return QueryResponse(query=query, error=result.error)


""" Twitter """


@app.get(f"/{modules['twitter']}/")
async def handle_get_twitter() -> QueryResponse:
    return await Run.query(CacheQuery(service="twitter", item_key="id_str"))


@app.get(f"/{modules['twitter']}/search/")
async def handle_search_tweets(keywords: str) -> QueryResponse:
    results = await search_tweets(keywords)
    query = Query(service=[modules['twitter']])
    return QueryResponse(query=query, results=results, results_count=len(results))


""" Wikis """


@app.get(f"/{modules['wiki']}/search/")
async def handle_search_wikis(keywords: str) -> QueryResponse:
    results = await search_wikis_as_list(keywords)
    query = Query(service=modules['wiki'])
    return QueryResponse(query=query, results=results, results_count=len(results))
