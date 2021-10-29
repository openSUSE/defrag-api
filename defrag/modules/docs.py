from defrag.modules.helpers.requests import Session
from lunr import lunr
from lunr.index import Index
from bs4 import BeautifulSoup
from pydantic import BaseModel
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, List, Tuple
from functools import partial

import asyncio
import json
import sys

__MOD_NAME__ = "documentation"


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
    try:
        result = await Session().get(indexes[source]["url"])
        if source == "tumbleweed":
            return await result.read()
        return await result.text()
    except Exception as error:
        print("ERROR", str(error))
        raise Exception("My error", error)


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


async def create_indexes_in_parallel() -> Tuple[Index, Index]:
    leap_data, tw_data = await asyncio.gather(get_data("leap"), get_data("tumbleweed"))
    loop = asyncio.get_event_loop()
    sys.setrecursionlimit(0x100000)
    with ProcessPoolExecutor(max_workers=2) as executor:
        _make_leap = partial(make_leap_index, raw=leap_data)
        _make_tw = partial(make_tumbleweed_index, raw=tw_data)
        leap_res, tw_res = await asyncio.gather(
            loop.run_in_executor(executor, _make_leap), 
            loop.run_in_executor(executor, _make_tw)
        )
        return leap_res, tw_res


async def set_indexes() -> None:
    leap, tw = await create_indexes_in_parallel()
    set_global_index("leap", leap)
    set_global_index("tumbleweed", tw)
    print("Docs indexes ready.")


def ready_to_index(sources: List[str]) -> bool:
    for s in sources:
        if not indexes[s]["index"]:
            return False
    return True


async def search(keywords: str) -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=2) as executor:
        _search_leap = partial(search_index, idx=indexes["leap"]["index"], source="leap", keywords=keywords)
        _search_tw = partial(search_index, idx=indexes["tumbleweed"]["index"], source="tumbleweed", keywords=keywords)
        leap_res, tw_res = await asyncio.gather(
            loop.run_in_executor(executor, _search_leap),
            loop.run_in_executor(executor, _search_tw)
        )
        return leap_res + tw_res