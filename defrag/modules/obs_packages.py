from operator import attrgetter
from typing import Any, Dict, Generator, List
from aiohttp.helpers import BasicAuth
from defrag.modules.helpers.requests import Session
from requests import Request
from dataclasses import dataclass
import lxml.etree

from defrag import BUGZILLA_PASSWORD, BUGZILLA_USER

__MOD_NAME__ = "obs_packages"


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
        if not name in names:
            names.append(name)
            yield PackageEntry(**{k: v for k, v in i.items() if k in keys})


def is_relevant(entry: PackageEntry, home_repos: bool) -> bool:

    if "home:" in entry.project and not home_repos:
        return False

    """
    if any(sub in entry.repository.lower() for sub in ["tumbleweed", "opensuse"]):
        return False
    """

    if ":branches:" in entry.project:
        return False
    
    # removed 'devel'
    if any(sub in entry.name.lower() for sub in ["debuginfo", "debugsource", "buildsymbols", "lang", "l10n", "trans", "doc", "docs"]):
        return False

    if entry.arch == "src":
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
    if response.status != 200:
        raise Exception(
            f"Server responded with HTTP error code: {response.status}")
    dom = lxml.etree.fromstring(await response.text(), parser=None)
    return [{k: v for k, v in b.items()} for b in dom.xpath("/collection/binary")]
    

async def search(keyword: str, distribution: str, home_repos: bool, provider: str) -> List[Dict[str, str]]:
    if not distribution.lower() in ["leap", "tumbleweed"]:
        raise Exception(f"Invalid distribution name {distribution}")
    if not provider.lower() in ["opi", "osc"]:
        raise Exception(f"Invalid provider name {provider}")
    distribution = "openSUSE:Factory" if distribution == "tumbleweed" else "openSUSE:Leap:15.3"
    provider = "https://api.opensuse.org" if provider == "opi" else "https://pmbs.links2linux.de"
    q = OS_API_QUERY(
        provider,
        "/search/published/binary/id",
        distribution,
        keyword
    )
    items = await get_package_items(q.build())
    return to_dict(sort_on("name", (e for e in build(items) if is_relevant(e, home_repos))))
