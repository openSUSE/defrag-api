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

<<<<<<< HEAD
<<<<<<<< HEAD:defrag/modules/helpers/__init__.py
from typing import Dict, Any, List, Optional, Union
from pydantic.main import BaseModel


""" FIXME 
    make Query and subclasses subclass of pydantic `BaseModel`    
"""


class Query(BaseModel):
    service: str
    item_key: Optional[Union[int, str]]


class CacheQuery(Query):
    service: str
    item_key: Optional[Union[int, str]] = None


class QueryResponse(BaseModel):
    query: Query
    results_count: Optional[int] = None
    results: Optional[List[Any]] = None
    error: Optional[str] = None
========
name: Run Python Tests
on:
  push:
    branches:
      - main
      - dev
  pull_request:
    branches:
      - main
      - dev

jobs:
  tests:
    # TODO: It would be nice to run this on openSUSE
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2
      - name: Install Python 3
        uses: actions/setup-python@v1
        with:
          python-version: 3.8
      - name: Install dependencies
        run: |
          python3 -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests with pytest
        run: pytest
>>>>>>>> ec2bf616fed091c17a6e8b1c3c91b089e038ffe2:.github/workflows/ci.yaml
=======
from typing import Dict, Any


class QueryObject:
    def __init__(self, query: Dict[Any, Any]):
        self.context = query

    def __repr__(self):
        return "<Query Object>"
>>>>>>> ec2bf616fed091c17a6e8b1c3c91b089e038ffe2
