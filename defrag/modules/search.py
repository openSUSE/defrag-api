from importlib import import_module
from defrag.modules import LOADED
from typing import List
from pydantic import BaseModel

__MOD_NAME__ = "global_search"

search_map = {f: getattr(m, "search") for f, m in [(n, import_module(
    f"defrag.modules.{n}")) for n in LOADED] if hasattr(m, "search")}


class SearchQuery(BaseModel):
    keywords: str
    scope: List[str]

