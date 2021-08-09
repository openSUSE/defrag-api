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

from typing import Dict, Any, List, Optional, Union
from pydantic.main import BaseModel


""" FIXME 
    make Query and subclasses subclass of pydantic `BaseModel`    
"""


class Query(BaseModel):
    service: str


class CacheQuery(Query):
    service: str
    item_key: Optional[Union[int, str]] = None


class QueryResponse(BaseModel):
    query: Query
    results_count: Optional[int] = None
    results: Optional[List[Any]] = None
    error: Optional[str] = None
