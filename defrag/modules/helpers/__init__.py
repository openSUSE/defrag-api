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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Any, Callable, Dict, List, Optional, Union
from pydantic.main import BaseModel

""" FIXME 
    make Query and subclasses subclass of pydantic `BaseModel`    
"""


class Query(BaseModel):
    service: str
    item_id: Optional[Union[int, str]]


class CacheQuery(Query):

    filter_pred: Optional[Callable[[Any], bool]] = None
    sort_on_key: Optional[str] = None
    reverse: bool = False
    count: Optional[int] = None

    def __init__(
        self,
        service: str,
        item_id: Optional[Union[int, str]] = None,
        filter_pred: Optional[Callable[[Any], bool]] = None,
        sort_on_key: Optional[str] = None,
        reverse: bool = False,
        count: Optional[int] = None
    ) -> None:
        super().__init__(**{"service": service, "id_key": item_id})
        self.filter_pred = filter_pred
        self.sort_on_key = sort_on_key
        self.reverse = reverse
        self.count = count


class QueryResponse(BaseModel):
    query: Query
    results_count: Optional[int] = None
    results: Optional[Union[List[Any], Dict[str, Any]]] = None
    error: Optional[str] = None
    message: Optional[str]


class EitherErrorOrOk:

    def __init__(self, error: Optional[str] = None, ok: Optional[Union[Dict[str, Any], List[Any], str]] = None, ok_msg: Optional[str] = None) -> None:
        if error and ok:
            raise Exception("Either error XOR ok!!")
        elif error:
            self.error = error
        else:
            self.ok = ok
        if ok_msg:
            self.ok_msg = ok_msg

    def dict(self) -> Dict[str, Any]:
        res = {"ok": self.ok} if hasattr(self, "ok") else {"error": self.error}
        if hasattr(self, "ok_msg"):
            return {**res, "ok_msg": self.ok_msg}
        return res

    def is_ok(self) -> Optional[Union[Dict[str, Any], List[Any], str]]:
        return self.ok if hasattr(self, "ok") else None


class FailuresAndSuccesses:

    def __init__(self, failures: List[Any], successes: List[Any]):
        self.successes = successes
        self.failures = failures

    def dict(self) -> Dict[str, List[Any]]:
        return {"successes": self.successes, "failures": self.failures}
