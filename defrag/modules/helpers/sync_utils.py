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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio
from functools import partial, wraps
from typing import Callable

"""
We want to use `as_async` and `to_async` in all these cases where we need to 
call from the main for CPU-bound computations without blocking the event loop.
Using 'None' as first parameter will offload the function call to a separate thread.
"""


def as_async_callback(f: Callable) -> Callable:
    @wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        f_saturated = partial(f, *args, **kwargs)
        loop.call_soon(f_saturated)
    return inner


def as_async(f: Callable) -> Callable:
    @wraps(f)
    async def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        f_saturated = partial(f, *args, **kwargs)
        return await loop.run_in_executor(None, f_saturated)
    return inner
