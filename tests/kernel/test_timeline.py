from sequence.kernel.entity import Entity
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline


class Dummy(Entity):
    def __init__(self, name, tl):
        Entity.__init__(self, name, tl)
        self.flag = False
        self.counter = 0

    def init(self):
        self.flag = True

    def op(self):
        self.counter += 1


def test_init():
    tl = Timeline()
    dummys = [Dummy(str(i), tl) for i in range(100)]
    for d in dummys:
        assert d.flag is False

    tl.init()
    for d in dummys:
        assert d.flag is True


def test_run():
    from numpy import random
    random.seed(0)
    tl = Timeline()
    dummy = Dummy("dummy", tl)
    times = random.random_integers(0, 20, 200)
    priorities = random.random_integers(0, 20, 200)

    for t, p in zip(times, priorities):
        process = Process(dummy, "op", [])
        e = Event(t, process, p)
        tl.schedule(e)

    tl.init()
    tl.run()

    assert dummy.counter == 200

    tl = Timeline(5)
    for t, p in zip(times, priorities):
        process = Process(dummy, "op", [])
        e = Event(t, process, p)
        tl.schedule(e)

    tl.init()
    tl.run()

    assert tl.now() == tl.time == 5 and len(tl.events) > 0
