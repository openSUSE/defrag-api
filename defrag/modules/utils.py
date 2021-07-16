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
from typing import Any, Callable, List, Tuple

__MOD_NAME__ = "utils"

"""
Some utilities for doing data manipulation.
"""


def compose(*funcs: Tuple[Callable]) -> Callable:
    def step(acc, f):
        return f(acc)

    def inner(seed):
        return reduce(step, funcs, seed)
    return inner


def test_compose():
    def inc(x): return x*2
    def double(x): return x+3
    func = compose(inc, double)
    res = func(1)
    assert res == 5


def make_transducer(transformer, reducer, baseCase) -> Callable:
    def transducer(seq):
        return reduce(transformer(reducer), seq, baseCase)
    return transducer


def test_make_transducer():

    def step(acc, val):
        acc.append(val)
        return acc

    def low3(acc, val):
        if val < 3:
            return step(acc, val)
        return acc

    def inc(step):
        def inner(acc, val):
            return step(acc, val+1)
        return inner

    transducer = make_transducer(inc, low3, [])
    res = transducer([0, 1, 2])
    assert res == [1, 2]


test_compose()
test_make_transducer()
