from defrag.modules.helpers.data_manipulation import compose, make_xform, make_transducer, base_step

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
    res = transducer([0, 1, 2])
    assert res == ["1", "2"]