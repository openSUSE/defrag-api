import json
from typing import Any, Coroutine, Dict, List, Optional
from lunr import lunr
from bs4 import BeautifulSoup
from lunr.index import Index
from defrag.modules.helpers.requests import Req
from defrag.modules.helpers import Query, QueryResponse
from defrag import app
from pydantic import BaseModel
import concurrent.futures
import asyncio
from itertools import chain

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
    async with Req(indexes[source]["url"]) as result:
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


def set_leap_index(docs: List[LunrDoc]) -> Index:
    listed = [doc.dict() for doc in docs]
    idx = lunr(ref="permalink", fields=("contents", "title"), documents=listed)
    indexes["leap"]["index"] = idx
    return idx


def set_tumbleweed_index(raw: bytes) -> Index:
    serialized: Dict[str, Any] = json.loads(raw)["index"]
    new_idx = Index.load(serialized)
    indexes["tumbleweed"]["index"] = new_idx
    idx = new_idx
    return idx


def thin_prime(item: Dict[str, Any], source: str) -> Dict[str, Any]:
    built = {k: item[k] for k in item if k in ["score", "ref"]}
    built["source"] = source
    return built


def sorted_on_score(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(items, key=lambda x: x["score"], reverse=True)


def render(items: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    return sorted_on_score((list(map(lambda item: thin_prime(item, source), items))))


def search(keywords: str, source: str) -> List[Dict[str, Any]]:
    global indexes
    try:
        return indexes[source]["index"].search(keywords)
    except Exception as reason:
        print(
            f"Query {source} with {keywords} failed for this reason: {reason}")


async def ensure_index(source: str) -> None:
    global indexes
    idx = indexes[source]["index"]
    if source == "leap" and not idx:
        set_leap_index((make_soup(await get_data(source))))
    elif source == "tumbleweed" and not idx:
        set_tumbleweed_index(await get_data(source))


@app.get("/" + __MOD_NAME__ + "/single/{source}/{keywords}")
async def search_single_source_docs(keywords: str, source: str) -> QueryResponse:
    await ensure_index(source)
    rendered_results = render(search(keywords, source), source)
    return QueryResponse(query=Query(service="search_docs"), results_count=len(rendered_results), results=rendered_results)


def par_search(source: str, keywords: str):
    return list(map(lambda item: thin_prime(item, source), search(keywords, source)))


@app.get("/" + __MOD_NAME__ + "/merged/{keywords}")
async def search_merging_sources_docs(keywords: str) -> QueryResponse:
    rendered_results: List[Dict[str, Any]] = []
    if indexes["leap"]["index"] and indexes["tumbleweed"]["index"]:
        rendered_results = [i for i in chain.from_iterable(
            (list(map(lambda res: thin_prime(res, source), search(keywords, source))) for source in ["tumbleweed", "leap"]))]
    else:
        await asyncio.gather(ensure_index("tumbleweed"), ensure_index("leap"))
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
            leap = executor.submit(
                par_search, **{"source": "leap", "keywords": keywords})
            tw = executor.submit(
                par_search, **{"source": "tumbleweed", "keywords": keywords})
            rendered_results = leap.result() + tw.result()
    sorted_results = sorted_on_score(rendered_results)
    return QueryResponse(query=Query(service="search_docs"), results_count=len(rendered_results), results=sorted_results)
