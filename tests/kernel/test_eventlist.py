from sequence.kernel.event import Event
from sequence.kernel.eventlist import EventList


def test_push():
    el = EventList()
    e = Event(0, None)
    el.push(e)
    e = Event(0, None, 1)
    el.push(e)


def test_pop():
    from numpy import random
    random.seed(0)
    times = list(random.random_integers(0, 100, 10))
    el = EventList()
    for t in times:
        e = Event(t, None)
        el.push(e)
    times.sort()
    while el.isempty() is False:
        assert times.pop(0) == el.pop().time

    priorities = list(random.random_integers(0, 100, 10))
    el = EventList()
    for p in priorities:
        e = Event(5, None, p)
        el.push(e)
    priorities.sort()
    while el.isempty() is False:
        assert priorities.pop(0) == el.pop().priority


def test_isempty():
    el = EventList()
    assert el.isempty() is True
    e = Event(0, None)
    el.push(e)
    assert el.isempty() is False
    e1 = el.pop()
    assert el.isempty() is True


def test_len():
    el = EventList()
    assert len(el) == 0
    e = Event(0, None)
    el.push(e)
    assert len(el) == 1
    e1 = el.pop()
    assert len(el) == 0
    assert e == e1

def test_remove():
    el = EventList()
    e1 = Event(0, None)
    e2 = Event(1, None)
    el.push(e1)
    el.push(e2)
    assert el.data[0] == e1
    el.remove(e1)
    assert el.data[0] == e2
    el.pop()
    assert len(el) == 0
    e3 = Event(2, None)
    e4 = Event(2, None)
    el.push(e3)
    el.push(e4)
    el.remove(e3)
    top_e = el.pop()
    assert len(el) == 0 and id(top_e) == id(e4) != id(e3) and top_e == e3
