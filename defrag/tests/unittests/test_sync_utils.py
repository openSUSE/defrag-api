import asyncio
from defrag.modules.helpers.sync_utils import as_async, as_async_callback
import pytest
from time import sleep

@pytest.mark.asyncio
async def test_sync_utils():
    please_inc_me = 0
    @as_async
    def my_io_bound_function():
        sleep(1)
        return 1
    @as_async_callback
    def my_io_bound_function_as_callback():
        nonlocal please_inc_me
        sleep(1)
        please_inc_me += 1
    my_io_bound_function_as_callback()
    res = await my_io_bound_function()
    please_inc_me += res
    assert please_inc_me == 2


    