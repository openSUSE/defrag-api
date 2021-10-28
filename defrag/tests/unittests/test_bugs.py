from defrag.modules.helpers.requests import Session
import pytest
from defrag.modules.bugs import BugzillaQueryEntry, search, search_bugs_with_term, search_all_bugs, register_service, login
from defrag.modules.db.redis import RedisPool


def test_login():
    handler = login()
    assert handler.logged_in


@pytest.mark.asyncio  # needed to have a running loop later in the call stack
async def test_register():
    register_service()


@pytest.mark.asyncio
async def test_endpoint(term="wayland"):
    response = await Session().get(f"https://bugzilla.opensuse.org/buglist.cgi?quicksearch={term}")
    res = await response.text()
    assert res


@pytest.mark.asyncio
async def test_global_search(term="wayland"):
    res = await search(term)
    assert res


@pytest.mark.asyncio
async def test_search_bugs_with_term():
    with RedisPool() as connection:
        connection.flushall()
    res = await search_bugs_with_term("wayland")
    assert res


@pytest.mark.asyncio
async def test_search_all_bugs():
    with RedisPool() as connection:
        connection.flushall()
    query = BugzillaQueryEntry(search_string="wayland")
    res = await search_all_bugs(query)
    assert res
