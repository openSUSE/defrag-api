import asyncio
from typing import Any, Dict, List, Optional
import bugzilla
from datetime import datetime
from bugzilla.base import Bugzilla
from pydantic.main import BaseModel


from defrag.modules.helpers import Query, CacheQuery, QueryResponse
from defrag.modules.helpers.cache_manager import Cache, Memo_Redis, Run, Service
from defrag import app, BUGZILLA_USER, BUGZILLA_PASSWORD
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.exceptions import ParsingException
from defrag.modules.helpers.requests import Req
from bs4 import BeautifulSoup

__MOD_NAME__ = "bugs"

URL = "https://bugzilla.opensuse.org/xmlrpc.cgi"
bzapi = bugzilla.Bugzilla(url=URL)


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
        # Now you can iterate over these instances dict-style: `for k, v in
        # entry: ...`
        for attr, value in self.dict().items():
            yield attr, value


def login() -> Bugzilla:
    global bzapi
    handler = bugzilla.Bugzilla(
        url=URL, user=BUGZILLA_USER, password=BUGZILLA_PASSWORD)
    if not handler.logged_in:
        raise Exception(
            "Login failed. Please double-check the credentials provided by your environment.")
    bzapi = handler
    return handler  # needed for the tests


async def get_this_bug(bug_id: int) -> BugzillaQueryEntry:
    if not bzapi.logged_in:
        login()
    bug = await as_async(bzapi.getbug)(bug_id)
    building_bug = BugzillaQueryEntry()
    for attr, _ in building_bug:
        # Builds a bug instance from the matching fields on the fetched data.
        if hasattr(bug, attr):
            setattr(building_bug, attr, getattr(bug, attr))
    return building_bug


async def search_bugs_with_term(term: str) -> List[int]:
    try:
        async with Req(f"https://bugzilla.opensuse.org/buglist.cgi?quicksearch={term}") as response:
            if response.status == 200:
                text = await response.text()
                soup = BeautifulSoup(text, "lxml")
                bz_result_count = soup.find(
                    "span", {"class": "bz_result_count"})
                result = []
                if bz_result_count.find("span",
                                        {"class": "zero_results"}) is None:
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
    except Exception as exp:
        raise exp


async def search_all_bugs(query: BugzillaQueryEntry) -> List[Dict[str, Any]]:
    if not query.search_string:
        return []
    bugs_ids = await search_bugs_with_term(query.search_string)
    if not bugs_ids:
        return []
    results = []
    # careful, apparently if we launch all coroutines concurrently or remove the limit, the
    # server denies us!
    for res in asyncio.as_completed(
            [get_this_bug(bug_id) for n, bug_id in enumerate(bugs_ids) if n < 26]):
        model = await res
        results.append({**model.dict(exclude_unset=True),
                       **model.dict(exclude_none=True)})
    return results


def register_service():
    service = Service(datetime.now(), store=None)
    Cache.register_service(__MOD_NAME__, service)


@app.get("/" + __MOD_NAME__ + "/")
async def root() -> QueryResponse:
    return QueryResponse(query="info", results=[
                         {"module": "Bugzilla", "description": "Get information about bugs on bugzilla.opensuse.org"}])

@app.get("/" + __MOD_NAME__ + "/bug/{bug_id}")
@Memo_Redis.install_decorator("/" + __MOD_NAME__ + "/bug/")
async def get_bug(bug_id: int) -> QueryResponse:
    query = CacheQuery(service="bugs", item_id=bug_id)
    async with Run(query) as response:
        return response


@app.get("/" + __MOD_NAME__ + "/search/")
@Memo_Redis.install_decorator("/" + __MOD_NAME__ + "/search/")
async def search(term: str) -> QueryResponse:
    query = BugzillaQueryEntry(search_string=term)
    result = await search_all_bugs(query)
    return QueryResponse(query=Query(service="bugs"),results_count=len(result),results=result)
