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

from functools import reduce
from typing import Any, Callable, Tuple

__MOD_NAME__ = "utils"

"""
Some utilities for doing data manipulation.
"""


def composeFrom(seed: Any, *funcs: Callable) -> Any:
    def inner(acc: Tuple[Callable], f: Callable) -> Any:
        return f(acc)
    return reduce(inner, funcs, seed)


def test_composeFrom() -> None:
    def inc(x): return x+1
    def double(x): return x*2
    assert composeFrom(0, inc, double) == 2