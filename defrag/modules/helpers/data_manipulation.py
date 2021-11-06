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
from itertools import islice
from typing import Any, Callable, Deque, Dict, Generator, Iterable, List, Optional, Tuple

from pottery.dict import RedisDict

"""
Utilities for data manipulation.
"""

# Base


def compose(*funcs: Tuple[Callable]) -> Callable:
    """ Compose multiple functions (right-associative) """
    def step(acc, f):
        return f(acc)

    def inner(seed):
        return reduce(step, funcs, seed)
    return inner


# Clojure-style transducers


def base_step(acc, val):
    acc.append(val)
    return acc


def make_xform(*reducers: Tuple[Callable]) -> Callable:
    return reduce(compose, reducers)


def make_transducer(xform: Callable, step: Callable, folder: List[Any] = []) -> Callable:
    """ 'Transduce' over a transformer and a step function into a given folder
    The composition of functions as 'xform' applies right to left (right-associative). See test below. """
    def transducer(seq):
        return reduce(xform(step), seq, folder)
    return transducer


# Special reducers


def partition_left_right(xs: Iterable, predicate: Callable) -> Tuple[List[Any], List[Any]]:
    def reducer(acc, val):
        left, right = acc
        if predicate(val):
            right.append(val)
        else:
            left.append(val)
        return acc
    return reduce(reducer, xs, ([], []))


# Operations on Deque


def find_index(n: int, q: Deque) -> int:
    """
    Assuming the container is a inverse partial order.
    If the ordered things are timestamps in descending order:
    [ m = remote future, m - k = close future, n < m = soon ... ]
    'find_index' corresponds to 'find next timestamp'.
    """
    if not q:
        return 0
    left, right = q[0], q[-1]
    if n > left:
        return 0
    if n < right:
        return -1
    counter = 0
    for x in reversed(q):
        if n >= x:
            break
        counter += 1
    return counter


def insert_one(n: int, q: Deque) -> Deque:
    i = find_index(n, q)
    if i == 0:
        q.appendleft(n)
    elif i == -1:
        q.append(n)
    else:
        q.insert(i, n)
    return q


def insert_many(l: List[int], q: Deque) -> Deque:
    if l:
        return insert_many(l, insert_one(l.pop(), q))
    return q


def schedule_fairly(
    due, 
    key: str,
    filt: Callable[[Any], bool]
) -> Generator[Tuple[str, float], None, None]:
    """
    Assuming 'due: Dic[int, Dict[str, Any]]',
    where one of the Any is List[float] encoding timestamps for the Dict[str, Any] event to which they belong,
    this generator functions yields all timestamps satisfying the 'filt' predicate
    in a "fair" round-robin order.
    """
    if not isinstance(due, RedisDict) and not isinstance(due, Dict):
        raise Exception("Cannot schedule_farily from non Redict object")
    pipes = {k: (sched for sched in reversed(item[key])) for k, item in due.items()}
    keys = list(pipes.keys())
    index = 0
    while keys:
        try:
            index = index + 1 if index < len(keys) - 1 else 0
            val = next(pipes[keys[index]])
            if filt(val):
                yield (keys[index], val)
        except StopIteration:
            keys.remove(keys[index])