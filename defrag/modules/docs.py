from defrag import app
from defrag.modules.helpers.services_manager import Controllers, ServiceTemplate, ServicesManager
from defrag.modules.helpers.requests import Req
from defrag.modules.helpers import Query, QueryResponse
from lunr import lunr
from lunr.index import Index
from bs4 import BeautifulSoup
from pydantic import BaseModel
from concurrent.futures import ProcessPoolExecutor
import asyncio
import json
import sys
from typing import Any, Dict, List, Tuple

__MOD_NAME__ = "docs"


class LunrDoc(BaseModel):
    number: str
    contents: str
    permalink: str
    title: str


indexes = {
    "leap": {
        "url": "https://doc.opensuse.org/documentation/leap/reference/single-html/book-reference/index.html",
        "index": None,
    },
    "tumbleweed": {
        "url": "https://raw.githubusercontent.com/openSUSE/openSUSE-docs-revamped-temp/gh-pages/search/search_index.json",
        "index": None
    }
}


async def get_data(source: str) -> Any:
    async with Req(indexes[source]["url"], closeOnResponse=False) as result:
        if source == "tumbleweed":
            return await result.read()
        return await result.text()


def make_soup(data_str: str) -> List[LunrDoc]:
    root = BeautifulSoup(data_str, 'html.parser')
    chapters = root.find_all(class_="chapter")
    res = []
    for c in chapters:
        titles = c.find_all(class_="titlepage")
        contents = [c.get_text() for c in c.find_all("p")]
        for i, t in enumerate(titles):
            names = t.find_all(class_="name")[0].get_text()
            permalink = t.find_all(class_="permalink")[0]["href"]
            number = t.find_all(class_="number")[0].get_text().strip()
            res.append(LunrDoc(number=number, title=names,
                       permalink=permalink, contents="".join(contents[i])))
    return res


def make_leap_index(raw: str) -> Index:
    docs: List[LunrDoc] = make_soup(raw)
    listed: List[Dict[str, Any]] = [doc.dict() for doc in docs]
    idx = lunr(ref="permalink", fields=("contents", "title"), documents=listed)
    return idx


def make_tumbleweed_index(raw: bytes) -> Index:
    serialized: Dict[str, Any] = json.loads(raw)["index"]
    return Index.load(serialized)


def thin_prime(source: str, item: Dict[str, Any]) -> Dict[str, Any]:
    built = {k: item[k] for k in item if k in ["score", "ref"]}
    built["source"] = source
    return built


def sorted_on_score(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(items, key=lambda x: x["score"], reverse=True)


def search_index(idx: Index, source: str, keywords: str) -> List[Dict[str, Any]]:
    return list(map(lambda item: thin_prime(source, item), idx.search(keywords)))


def set_global_index(source: str, idx: Index) -> None:
    global indexes
    indexes[source]["index"] = idx


def ready_to_index(sources: List[str]) -> bool:
    for s in sources:
        if not indexes[s]["index"]:
            return False
    return True


def make_index_search_leap(leap_data: str, keywords: str) -> Tuple[Index, List[Dict[str, Any]]]:
    idx = make_leap_index(leap_data)
    return idx, search_index(idx, "leap", keywords)


def make_index_search_tumbleweed(tw_data: bytes, keywords: str) -> Tuple[Index, List[Dict[str, Any]]]:
    idx = make_tumbleweed_index(tw_data)
    return idx, search_index(idx, "tumbleweed", keywords)


async def make_search_set_indexes_in_parallel(keywords: str) -> List[Dict[str, Any]]:

    leap, tw = await asyncio.gather(get_data("leap"), get_data("tumbleweed"))
    results = []
    sys.setrecursionlimit(0x100000)
    with ProcessPoolExecutor(max_workers=2) as executor:
        leap_worker = executor.submit(
            make_index_search_leap, **{"leap_data": leap, "keywords": keywords})
        tw_worker = executor.submit(
            make_index_search_tumbleweed, **{"tw_data": tw, "keywords": keywords})
        leap_index, leap_results = leap_worker.result()
        tw_index, tw_results = tw_worker.result()
        set_global_index("leap", leap_index)
        set_global_index("tumbleweed", tw_index)
        results = leap_results + tw_results
    return results


def search_indexes_in_parallel(keywords: str) -> List[Dict[str, Any]]:
    with ProcessPoolExecutor(max_workers=2) as executor:
        leap_worker = executor.submit(
            search_index, **{"idx": indexes["leap"]["index"], "source": "leap", "keywords": keywords})
        tw_worker = executor.submit(
            search_index, **{"idx": indexes["tumbleweed"]["index"], "source": "tumbleweed", "keywords": keywords})
        results = leap_worker.result() + tw_worker.result()
    return results


@app.get("/" + __MOD_NAME__ + "/single/{source}/{keywords}")
async def search_single_source_docs(source: str, keywords: str) -> QueryResponse:
    if not ready_to_index([source]):
        if source == "tumbleweed":
            set_global_index("tumbleweed", make_tumbleweed_index(await get_data(source)))
        else:
            set_global_index("leap", make_leap_index(await get_data(source)))
    results = sorted_on_score(search_index(
        indexes[source]["index"], source, keywords))
    return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)


@app.get("/" + __MOD_NAME__ + "/merged/{keywords}")
async def search_merging_sources_docs(keywords: str) -> QueryResponse:
    if not ready_to_index(["leap", "tumbleweed"]):
        results = await make_search_set_indexes_in_parallel(keywords)
        return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)
    else:
        results = sorted_on_score(search_indexes_in_parallel(keywords))
        return QueryResponse(query=Query(service="search_docs"), results_count=len(results), results=results)


def register():
    template = ServiceTemplate(__MOD_NAME__, None, None, None, None)
    service = ServicesManager.realize_service_template(template, None)
    ServicesManager.register_service(__MOD_NAME__, service)
