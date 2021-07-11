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

from defrag.modules.helpers.caching import cache
from defrag.modules.helpers import QueryObject
from defrag import app
from fastapi.testclient import TestClient

@cache
def dummy_function(query: QueryObject):
    return {"result": "Nothing"}

@app.get("/tests/cache")
async def cache_endpoint():
    query = QueryObject({"term": "Test"})
    result = dummy_function(query)
    return result

def test_cache():
    client = TestClient(app)
    response = client.get("/tests/cache")
    # Do it twice so that it is cached
    response = client.get("/tests/cache")
    assert response.json() == {"result": "Nothing", "cached": True}
