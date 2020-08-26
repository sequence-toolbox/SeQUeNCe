from sequence.kernel.entity import Entity
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline


class Dummy(Entity):
    def __init__(self, name, tl):
        Entity.__init__(self, name, tl)
        self.flag = False
        self.counter = 0
        self.click_time = None

    def init(self):
        self.flag = True

    def op(self):
        self.counter += 1

    def click(self):
        self.click_time = self.timeline.now()


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
    times = random.randint(0, 20, 200)
    priorities = random.randint(0, 20, 200)

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

    assert tl.now() == tl.time < 5 and len(tl.events) > 0


def test_remove_event():
    tl = Timeline()
    dummy = Dummy('1', tl)
    event = Event(1, Process(dummy, 'op', []))
    d2 = Dummy('2', tl)
    event2 = Event(1, Process(d2, 'op', []))
    tl.schedule(event)
    tl.schedule(event2)
    tl.init()
    assert dummy.counter == 0 and d2.counter == 0
    tl.remove_event(event)
    tl.run()
    assert dummy.counter == 0 and d2.counter == 1


def test_update_event_time():
    tl = Timeline()
    d1 = Dummy('1', tl)
    event1 = Event(10, Process(d1, 'click', []))
    d2 = Dummy('2', tl)
    event2 = Event(10, Process(d2, 'click', []))

    tl.schedule(event1)
    tl.schedule(event2)
    tl.init()
    assert d1.click_time is None and d2.click_time is None
    tl.update_event_time(event2, 20)
    tl.run()

    assert d1.click_time == 10 and d2.click_time == 20
