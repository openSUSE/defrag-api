import asyncio
from functools import partial
from bugzilla.base import Bugzilla
from pydantic.main import BaseModel
from defrag.modules.helpers import CacheQuery, QueryResponse
from defrag.modules.helpers.services_manager import Run, ServiceTemplate, ServicesManager
from defrag.modules.helpers.cache_stores import CacheStrategy, DStore, RedisCacheStrategy
from typing import Any, List, Optional
from defrag import app
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.exceptions import ParsingException
from defrag.modules.helpers.requests import Req
from bs4 import BeautifulSoup
from os import environ as env
import bugzilla

__MOD_NAME__ = "bugs"

URL = "https://bugzilla.opensuse.org/xmlrpc.cgi"
bzapi: bugzilla.Bugzilla


class BugzillaQueryEntry(BaseModel):
    # I changed this class to fill two roles:
    # - captures the parameters in a user's request to an endpoint
    # - stores the data fetched by the parser.
    search_string: Optional[str] = None
    bug_id: Optional[int] = None
    product: Optional[str] = None
    component: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    resolution: Optional[str] = None

    def url(self) -> str:
        return f"https://{URL}/show_bug.cgi?id={self.bug_id}"

    def __iter__(self):
        # Now you can iterate over these instances dict-style: `for k, v in entry: ...`
        for attr, value in self.dict().items():
            yield attr, value


def login() -> Bugzilla:
    global bzapi
    handler = bugzilla.Bugzilla(
        url=URL, user=env["BUGZILLA_USER"], password=env["BUGZILLA_PASSWORD"])
    if not handler.logged_in:
        raise Exception(
            "Login failed. Please double-check the credentials provided by your environment.")
    bzapi = handler
    return handler  # needed for the tests


async def get_this_bug(bug_id: int) -> BugzillaQueryEntry:
    # I was not really able to make something good out of this try...except block
    # do change this is you have a good idea
    """
    try:
    """
    bug = await as_async(bzapi.getbug)(bug_id)
    building_bug = BugzillaQueryEntry()
    for attr, _ in building_bug:
        # Builds a bug instance from the matching fields on the fetched data.
        if hasattr(bug, attr):
            setattr(building_bug, attr, getattr(bug, attr))
    return building_bug
    """    
    except bugzilla.BugzillaError as exp:
        LOGGER.error(
            f"Error occured while getting bug from Bugzilla: {exp.get_bugzilla_error_string} (Error code {exp.get_bugzilla_error_code})")
        # I was not able to fix this. Can you take a look?
        raise BugzillaException(
            exp.get_bugzilla_error_string +
            f"({exp.get_bugzilla_error_code})")
    """


async def search_bugs_with_term(term: str) -> List[int]:
    # the parser seems to choke on something. You think you can fix?
    try:
        async with Req(f"https://bugzilla.opensuse.org/buglist.cgi?quicksearch={term}") as response:
            if response.status == 200:
                text = await response.text()
                soup = BeautifulSoup(text, "lxml")
                bz_result_count = soup.find(
                    "span", {"class": "bz_result_count"})
                result = []
                if bz_result_count.find("span", {"class": "zero_results"}) is None:
                    # I think we can just use the length of the list or?
                    """ count = re.findall(r'\d+', bz_result_count.text)[0] """
                    bz_buglist = soup.find(
                        "table", {
                            "class": "bz_buglist"}).findAll(
                        "tr", {
                            "class": "bz_bugitem"})
                    for row in bz_buglist:
                        columns = row.findAll("td")
                        if len(columns) == 8:
                            id = int(columns[0].text.replace("\n", ""))
                            result.append(id)
                return result
            else:
                raise ParsingException("Unknown error occured")
        # moved your exceptions catchers to the Req class. Thank you for them!
    except Exception as exp:
        raise exp

async def search_all_bugs(query: BugzillaQueryEntry):
    if not query.search_string:
        return []
    bugs_ids = await search_bugs_with_term(query.search_string)
    if not bugs_ids:
        return []
    results = []
    # careful, apparently if we launch all coroutines concurrently or remove the limit, the 
    # server denies us!
    for res in asyncio.as_completed([get_this_bug(bug_id) for n, bug_id in enumerate(bugs_ids) if n < 26]):
        results.append(await res)
    return results


class BugzillaStore(DStore):
    """ 
    We need to declare this class to be able make these two methods available to the Cache.

    If we assume that your cache store is RedisDict, pottery's dict-like datastructure,
    refreshing your entire store is as simple as reassigning on every key.

    The update is defined in 'cache_store.py:DStore:update_container_return_fresh_items` because
    it is generic to any store using this type of datastructure.
    """

    @staticmethod
    async def fetch_items():
        # This method is used to refresh the cache as a background task.
        # Let's not use for now because for now you just want to refresh the cache only on cache misses.
        pass

    def filter_fresh_items(self, fetch_items: List[Any]):
        # Filters out bugs whose id is not already a key in the cache dict.
        return [i for i in fetch_items if not i[self.dict_key] in self.container]


def register_service():
    # declares which key in Redis the cache container should be named with
    redis_key = __MOD_NAME__ + "_default"
    # declares how the cache beaviour should be for this service
    bugzilla_strategy = CacheStrategy(
        RedisCacheStrategy(populate_on_startup=False, auto_refresh=False, auto_refresh_delay=None, runner_timeout=None, cache_decay=None), None)
    bugzilla = ServiceTemplate(name=__MOD_NAME__, cache_strategy=bugzilla_strategy,
                               endpoint=None, port=None, credentials=None, custom_parameters=None)
    # connects together the cache behaviour and the actual cache store
    # notice the `dict_key` parameter: it is used to tell the cache that if you pass it a list of
    # BugzillaQueryEntry instances, it should use their 'bug_id' attribute as keys.
    service = ServicesManager.realize_service_template(
        bugzilla, BugzillaStore(redis_key=redis_key, dict_key="bug_id"))
    # sends everything to the ServicesManager for registration
    ServicesManager.register_service(__MOD_NAME__, service)


@app.get("/" + __MOD_NAME__ + "/bug/{bug_id}")
async def get_bug(bug_id: int) -> QueryResponse:
    # declares how this request should interface with the cache
    cache_query = CacheQuery(service="bugs", item_key=bug_id)
    # declares what function to run if the item the request is looking for cannot find it in the cache store
    fallback = partial(get_this_bug, bug_id)
    # run the request
    return await Run.query(cache_query, fallback)


@app.get("/" + __MOD_NAME__ + "/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[{"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])


@app.get("/" + __MOD_NAME__ + "/search/")
async def search(query: BugzillaQueryEntry) -> QueryResponse:
    # declares how this request should interface with the cache
    # but perhaps the user did't pick the right endpoint has passed a bug id?
    if query.bug_id:
        fallback = partial(get_this_bug, query.bug_id)
        cache_query = CacheQuery(service="bugs", item_key=query.bug_id)
        return await Run.query(cache_query, fallback)
    # declares what function to run if the item the request is looking for cannot find it in the cache store
    fallback = partial(search_all_bugs, query)
    # run the request
    return await Run.query(CacheQuery(service="bugs"), fallback)
