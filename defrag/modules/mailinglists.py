import asyncio
import feedparser
from rank_bm25 import BM25Okapi

from typing import Any, Dict, Generator, List, NamedTuple, Optional
from defrag.modules.helpers.requests import Session

""" 
    INFO
    This modules polls recent RSS feeds exposed by the openSUSE mailing lists
"""

__MOD_NAME__ = "mailinglists"


class MailingListEntry(NamedTuple):
    author_detail: str
    id: str
    title: str
    title_detail: str
    link: str
    summary: str
    summary_detail: str
    published: str

    @classmethod
    def into(cls, entry: Dict[str, Any]):
        d = {k: v for k, v in entry.items() if k in cls._fields}
        return cls(**d)


class MailingLists:

    lists = [
        "admin",
        "announce",
        "board",
        "buildservice",
        "doc",
        "election-officials",
        "factory",
        "forums-admins"
        "heroes",
        "haskell",
        "kde",
        "membership-officials"
        "packaging",
        "project",
        "support",
        "web",
        "wiki",
        "yast-devels"
    ]

    feeds: Dict[str, List[MailingListEntry]] = {}
    bm_tokenized: Optional[BM25Okapi] = None
    corpus: List[Any] = []
    worker: Optional[asyncio.Task] = None
    interval = 21600 # 6 hours

    @classmethod
    def run_worker(cls) -> None:
        
        async def job():
            await cls.save_all_feeds()
            cls.init_tokenize_corpus()
        
        async def init_then_keep_polling():
            await job()
            while True:
                await asyncio.sleep(cls.interval)
                await job()

        if not cls.worker:
            cls.worker = asyncio.create_task(init_then_keep_polling())

    @classmethod
    async def fetch_one_feed(cls, list_name: str) -> bytes:
        res = await Session().get(cls.make_url(list_name))
        return await res.read()

    @classmethod
    async def save_all_feeds(cls) -> None:
        feeds = await asyncio.gather(*[cls.fetch_one_feed(l) for l in cls.lists])
        cls.feeds = {k: list(v) for k, v in zip(cls.lists, (cls.gen_parse_feed(f) for f in feeds))}

    @classmethod
    async def get_feed(cls, list_name: str) -> List[MailingListEntry]:
        if not list_name in cls.lists:
            raise Exception(
                f"Make sure all the names you pass are in on this list: {cls.lists}")
        if not cls.feeds:
            await cls.save_all_feeds()
        return list(cls.feeds[list_name])

    @classmethod
    async def get_feeds(cls, *lists_names) -> Dict[str, List[MailingListEntry]]:
        if any(not l in cls.lists for l in lists_names):
            raise Exception(
                f"Make sure all the names you pass are in on this list: {cls.lists}")
        if not cls.feeds:
            await cls.save_all_feeds()
        return {k: list(v) for k, v in cls.feeds.items() if k in lists_names}

    @classmethod
    def init_tokenize_corpus(cls) -> None:
        if not cls.feeds:
            raise Exception("Feeds must be fetched first!")
        tokenized = []
        corpus = []
        for l in MailingLists.feeds.values():
            tokenized += [e.title.lower().split(" ") +
                          e.title.lower().split(" ") for e in l]
            corpus += l
        cls.bm_tokenized = BM25Okapi(tokenized)
        cls.corpus = corpus
        print(f"Tokenized ({len(tokenized)}) and corpus ({len(corpus)}) done!")

    @staticmethod
    def search_idx(*keywords, result_n: int = 5) -> List[MailingListEntry]:
        if not MailingLists.bm_tokenized or not MailingLists.corpus:
            raise Exception("Index must be built before searching!")
        print(f"Searching with: {keywords}")
        return MailingLists.bm_tokenized.get_top_n(keywords, MailingLists.corpus, result_n)

    @staticmethod
    def make_url(list_name: str) -> str:
        if not list_name in MailingLists.lists:
            raise Exception(f"Not support mailing list: {list_name}")
        return f"https://lists.opensuse.org/archives/list/{list_name}@lists.opensuse.org/feed/"

    @staticmethod
    def gen_parse_feed(contents: bytes) -> Generator[MailingListEntry, None, None]:
        feed = feedparser.parse(contents)
        entries = (e for e in feed.entries)
        return (MailingListEntry.into(i) for i in entries)