import pytest
from defrag.modules.bugs import BugzillaQueryEntry, search_bugs_with_term, search_all_bugs, register_service, login
from defrag.modules.db.redis import RedisPool


def test_login():
    handler = login()
    assert handler.logged_in


@pytest.mark.asyncio
async def test_search_bugs_with_term():
    with RedisPool() as connection:
        connection.flushall()
    register_service()
    login()
    res = await search_bugs_with_term("wayland")
    assert res


@pytest.mark.asyncio
async def test_search_all_bugs():
    with RedisPool() as connection:
        connection.flushall()
    register_service()
    login()
    query = BugzillaQueryEntry(search_string="wayland")
    res = await search_all_bugs(query)
    assert res
