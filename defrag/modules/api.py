from operator import attrgetter
from typing import Any, Dict, Generator, List
from aiohttp.helpers import BasicAuth
from defrag.modules.helpers.requests import Session
from requests import Request
from dataclasses import dataclass
import lxml.etree

from defrag import BUGZILLA_PASSWORD, BUGZILLA_USER

__MOD_NAME__ = "api_opensuse"


@dataclass
class PreparedRequest:
    url: str


@dataclass
class OS_API_QUERY:
    base_url: str
    api_path: str
    distribution: str
    match_keyword: str

    def build(self) -> PreparedRequest:
        url_endpoint = self.base_url + self.api_path
        xpath = "contains-ic(@name, '%s') and path/project='%s'" % (
            self.match_keyword, self.distribution)
        prep_req = Request('GET', url_endpoint, params={
                           'match': xpath, "limit": 0}).prepare().url
        if not prep_req:
            raise Exception("Unable to build prepared request!")
        return PreparedRequest(prep_req)


@dataclass
class PackageEntry:
    arch: str
    baseproject: str
    filepath: str
    name: str
    package: str
    project: str
    release: str
    repository: str
    version: str


def build(items: List[Dict[str, Any]]) -> Generator[PackageEntry, None, None]:
    names = []
    keys = PackageEntry.__annotations__.keys()
    for i in items:
        name = i['name']
        if not name in names and is_relevant(i):
            names.append(name)
            yield PackageEntry(**{k: v for k, v in i.items() if k in keys})


def is_relevant(item: Dict[str, Any]) -> bool:

    if "home:" in item['project']:
        return False

    if any(sub in item['repository'].lower() for sub in ["tumbleweed", "opensuse"]):
        return False

    if ":branches:" in item['project']:
        return False

    if any(sub in item['name'].lower() for sub in ["debuginfo", "debugsource", "buildsymbols", "devel", "lang", "l10n", "trans", "doc", "docs"]):
        return False

    if item['arch'] == "src":
        return False

    return True


def sort_on(attr: str, entries: Generator[PackageEntry, None, None]) -> List[PackageEntry]:
    return sorted(entries, key=attrgetter(attr))


def render(es: List[PackageEntry]) -> str:
    return "\n***\n".join(["\n".join([f"{k}:{v}" for k, v in vars(e).items()]) for e in es])


def to_dict(es: List[PackageEntry]) -> List[Dict[str, str]]:
    return [vars(e) for e in es]


async def get_package_items(preq: PreparedRequest) -> List[Dict[str, Any]]:
    response = await Session().get(preq.url, auth=BasicAuth(BUGZILLA_USER, BUGZILLA_PASSWORD))
    if not response.status == 200:
        raise Exception(
            f"Server responded with HTTP error code: {response.status}")
    dom = lxml.etree.fromstring(await response.text(), parser=None)
    return [{k: v for k, v in b.items()} for b in dom.xpath("/collection/binary")]


async def search(keyword: str, distribution: str) -> List[Dict[str, str]]:
    if not distribution in ["Leap", "Tumbleweed"]:
        raise Exception(f"Invalid distribution name {distribution}")
    distribution = "openSUSE:Factory" if distribution == "Tumbleweed" else "openSUSE:Leap:15.3"
    q = OS_API_QUERY(
        "https://api.opensuse.org",
        "/search/published/binary/id",
        distribution,
        keyword
    )
    items = await get_package_items(q.build())
    return to_dict(sort_on("name", build(items)))
