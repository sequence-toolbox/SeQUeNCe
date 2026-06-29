from sequence.kernel.process import Process


def test_run():
    class Dummy():
        def __init__(self):
            self.counter = 0

        def add(self, x):
            self.counter += x

        def minus(self, x):
            self.counter -= x

    a = Dummy()
    b = Dummy()
    p1 = Process(a, "add", [1])
    assert a.counter == 0 and b.counter == 0
    p1.run()
    assert a.counter == 1 and b.counter == 0
    p2 = Process(b, "minus", [10])
    assert a.counter == 1 and b.counter == 0
    p2.run()
    assert a.counter == 1 and b.counter == -10
