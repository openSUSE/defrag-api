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


def base_step(acc, val):
    acc.append(val)
    return acc


def make_xform(*reducers: Tuple[Callable]) -> Callable:
    def inner(step):
        res = step
        for reduc in reducers:
            res = reduc(res)
        return res
    return inner


def make_transducer(xform: Callable, step: Callable, folder: List[Any] = []) -> Callable:
    """ The composition of functions as 'xform' applies right to left. See test below. """
    def transducer(seq):
        return reduce(xform(step), seq, folder)
    return transducer


def test_make_transducer():

    def to_str(_step):
        def inner(acc, val):
            return _step(acc, str(val))
        return inner

    def low3(_step):
        def inner(acc, val):
            if val < 3:
                return _step(acc, val)
            return acc
        return inner

    def inc1(_step):
        def inner(acc, val):
            return _step(acc, val+1)
        return inner

    xform = make_xform(to_str, low3, inc1)
    transducer = make_transducer(xform, base_step, [])
    res = transducer([0, 1, 2])
    assert res == ["1", "2"]


test_compose()
test_make_transducer()
