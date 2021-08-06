# Defrag - centralized API for the openSUSE Infrastructure
# Copyright (C) 2021 openSUSE contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Any, Dict, List, Tuple, Optional
from defrag import app, LOGGER
from defrag.modules.helpers import QueryObject
from defrag.modules.helpers.sync_utils import as_async
from defrag.modules.helpers.exceptions import BugzillaException, ParsingException, NetworkException
import bugzilla
from bugzilla import BugzillaError
from xmlrpc.client import Fault
from fastapi import Response, status
from defrag.modules.helpers.requests import Req
from bs4 import BeautifulSoup
import re
from attr import dataclass
import collections


URL = "bugzilla.opensuse.org"
bzapi = bugzilla.Bugzilla(URL)

__MOD_NAME__ = "bugs"


@dataclass
class BugZillaEntry:
    id: int
    product: Optional[str] = None
    component: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    resolution: Optional[str] = None

    def url(self) -> str:
        return f"https://{URL}/show_bug.cgi?id={self.id}"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "url": self.url()
        }
        if self.product:
            result["product"] = self.product
        if self.component:
            result["component"] = self.component
        if self.status:
            result["status"] = self.status
        if self.summary:
            result["summary"] = self.summary
        if self.resolution:
            result["resolution"] = self.resolution
        return result


BugList = collections.namedtuple('Buglist', ['count', 'list'])


@as_async
def get_bug_from_bugzilla(query: QueryObject) -> BugZillaEntry:
    try:
        bug = bzapi.getbug(query.context["id"])
    except BugzillaError as exp:
        LOGGER.error(
            f"Error occured while getting bug from Bugzilla: {exp.get_bugzilla_error_string} (Error code {exp.get_bugzilla_error_code})")
        raise BugzillaException(
            exp.get_bugzilla_error_string +
            f"({exp.get_bugzilla_error_code})")
    id = bug.id
    product, component, status, summary, resolution = None, None, None, None, None

    use_product = query.context["product"]
    use_component = query.context["component"]
    use_status = query.context["status"]
    use_resolution = query.context["resolution"]
    use_summary = query.context["summary"]

    if bug.product != "" and bug.product is not None and use_product:
        product = bug.product
    if bug.component != "" and bug.component is not None and use_component:
        component = bug.component
    if bug.status != "" and bug.status is not None and use_status:
        status = bug.status
    if bug.summary != "" and bug.summary is not None and use_summary:
        summary = bug.summary
    if bug.resolution != "" and bug.resolution is not None and use_resolution:
        resolution = bug.resolution
    result = BugZillaEntry(id, product, component, status, summary, resolution)
    return result


async def get_list_of_bugs(term: str) -> BugList:
    result = []
    count = 0
    async with Req(f"https://bugzilla.opensuse.org/buglist.cgi?quicksearch={term}") as response:
        try:
            if response.status == 200:
                text = await response.text()
                soup = BeautifulSoup(text, "lxml")
                bz_result_count = soup.find("span", {"class": "bz_result_count"})
                if bz_result_count.find("span", {"class": "zero_results"}) is None:
                    count = re.findall(r'\d+', bz_result_count.text)[0]
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
            else:
                raise ParsingException("Unknown error occured")
        except aiohttp.ClientResponseError as exp:
            raise NetworkException(f"{exp.status}: {exp.message}")
        except aiohttp.ServerTimeoutError as exp:
            raise NetworkException("Timeout.")
        except Exception as exp:
            raise exp
    r = BugList(count, result)
    return r


# This intenionally returns a dict so that it can get directly returned
# as json
async def universal_search(query: QueryObject) -> Dict[str, str]:
    term = query.context["term"]
    temp = await get_list_of_bugs(term)
    use_product = query.context["product"]
    use_component = query.context["component"]
    use_status = query.context["status"]
    use_resolution = query.context["resolution"]
    use_summary = query.context["summary"]
    result = {}
    result["number"] = temp.count
    hits = []
    use_metadata = use_product or use_component or use_status or use_resolution or use_summary
    for element in temp.list:
        bug_information = {}
        id = element
        bug_information["id"] = id
        bug_information["url"] = f"https://{URL}/show_bug.cgi?id={id}"
        if use_metadata:
            bug_query = {
                "id": id,
                "product": use_product,
                "component": use_component,
                "status": use_status,
                "resolution": use_resolution,
                "summary": use_summary,
            }
            bug = await get_bug_from_bugzilla(QueryObject(bug_query))
            bug_information = bug.to_dict()
        hits.append(bug_information)
    result["hits"] = hits
    return result


@app.get("/" + __MOD_NAME__ + "/bug/")
async def get_bug(id: int, response: Response, product: bool = True, component: bool = True, status: bool = True, resolution: bool = True, summary: bool = True) -> Dict[str, str]:
    query = {
        "id": id,
        "product": product,
        "component": component,
        "status": status,
        "resolution": resolution,
        "summary": summary
    }
    try:
        bug = await get_bug_from_bugzilla(QueryObject(query))
        return bug.to_dict()
    except Fault as ex:
        if ex.faultCode == 101:
            response.status_code = 404
            return {"error": ex.faultString}
        else:
            LOGGER.error(ex.faultString)
            response.status_code = 500
            return {"error": ex.faultString}
    except BugzillaException as ex:
        response.status_code = 500
        return {"error": ex.message}


@app.get("/" + __MOD_NAME__ + "/")
async def root() -> Dict[str, str]:
    return {
        "module": "Bugzilla",
        "description": "Get information about bugs on bugzilla.opensuse.org"}


@app.get("/" + __MOD_NAME__ + "/search/")
async def search(term: str, response: Response, product: bool = False, component: bool = False, status: bool = False, resolution: bool = False, summary: bool = False, url: bool = False) -> Dict[str, str]:
    query = {
        "term": term,
        "product": product,
        "component": component,
        "status": status,
        "resolution": resolution,
        "summary": summary,
        "url": url
    }
    try:
        return await universal_search(QueryObject(query))
    except NetworkException as exp:
        response.status_code = 503
        return {"error": exp.message}
    except BugzillaException as exp:
        response.status_code = 502
        return {"error": exp.message}
    except ParsingException as exp:
        response.status_code = 500
        return {"error": exp.message}
