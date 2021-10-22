from collections import deque
from defrag.modules.helpers.data_manipulation import compose, find_first, make_xform, make_transducer, base_step, filter_count_sort
from random import randint

def test_compose():
    def double(x: int) -> int: return x*2
    def plus3(x: int) -> int: return x+3
    func = compose(double, plus3)
    res = func(1)
    assert res == 5


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
    res = transducer([0, 1, 2, 3, 4])
    assert res == ["1", "2"]


def test_find_first():
    l = deque(sorted([1, 2, 5, 10, 3, 8, 4, 7, 5, 9, 2]))
    to_insert = 6
    def relation(item, origin): return origin < item
    index = find_first(l, relation, to_insert)
    l.insert(index, 6)
    assert l == deque([1, 2, 2, 3, 4, 5, 5, 6, 7, 8, 9, 10])
    m = deque([7])
    n = deque([5])
    index = find_first(m, relation, to_insert)
    m.insert(index, to_insert)
    assert m == deque([6, 7])
    index = find_first(m, relation, to_insert)
    n.insert(index, to_insert)
    assert n == deque([5, 6])
    to_insert = randint(0, 10000000)
    large = deque([x for x in range (0, 10000000)])
    index = find_first(large, relation, to_insert)
    d1 = len(large)
    large.insert(index, to_insert)
    d2 = len(large)
    assert d1 == d2-1  

def test_filter_count_sort():
    l = [1,2,3,4,5,6,7,8,9,10]
    assert filter_count_sort(l, lambda x: x > 5, 4, reverse=True) == [9,8,7,6]

