from sequence.kernel.event import Event
from sequence.kernel.eventlist import EventList
from numpy import random


MAX_TS = 100
MIN_TS = 0


def generate_event_list_with_random_time(seed: int, length: int) -> EventList:
    random.seed(seed)
    times = list(random.randint(MIN_TS, MAX_TS, length))
    el = EventList()
    for t in times:
        e = Event(t, None)
        el.push(e)
    return el


def test_push():
    el = EventList()
    e = Event(0, None)
    el.push(e)
    e = Event(0, None, 1)
    el.push(e)


def test_pop():
    el = generate_event_list_with_random_time(0, 10)
    last_ts = -float("inf")
    while not el.isempty():
        top_event = el.pop()
        assert top_event.time >= last_ts
        last_ts = top_event.time

    random.seed(0)
    priorities = list(random.randint(MIN_TS, MAX_TS, 10))
    el = EventList()
    for p in priorities:
        e = Event(5, None, p)
        el.push(e)
    last_priority = -float("inf")
    while not el.isempty():
        top_event = el.pop()
        assert top_event.priority >= last_priority
        last_priority = top_event.priority


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
    for e in el:
        assert not e.is_invalid()

    el.remove(e2)

    for e in el:
        if e == e1:
            assert not e.is_invalid()
        else:
            assert e.is_invalid()


def test_update_event_time():
    from numpy import random
    random.seed(0)

    # increase time
    for i in range(200):
        e = EventList()
        ts = [random.randint(1, 100) for _ in range(i + 10)]
        for t in ts:
            event = Event(t, None)
            e.push(event)

        index = random.randint(len(ts))
        agg_t = random.randint(25)
        event = e.data[index]

        e.update_event_time(event, event.time + agg_t)

        pre_time = -1
        while not e.isempty():
            event = e.pop()
            assert event.time >= pre_time
            pre_time = event.time

    # decrease time

    for i in range(200):
        e = EventList()
        ts = [random.randint(1, 100) for _ in range(i + 10)]
        for t in ts:
            event = Event(t, None)
            e.push(event)

        index = random.randint(len(ts))
        dec_t = random.randint(e.data[index].time)
        event = e.data[index]

        e.update_event_time(event, event.time - dec_t)

        pre_time = -1
        while not e.isempty():
            event = e.pop()
            assert event.time >= pre_time
            pre_time = event.time

    # same time
    for i in range(200):
        e = EventList()
        ts = [random.randint(1, 100) for _ in range(i + 10)]
        for t in ts:
            event = Event(t, None)
            e.push(event)

        index = random.randint(len(ts))
        event = e.data[index]

        e.update_event_time(event, event.time)

        pre_time = -1
        while not e.isempty():
            event = e.pop()
            assert event.time >= pre_time
            pre_time = event.time


def test_top():
    el = generate_event_list_with_random_time(0, 10)
    while not el.isempty():
        top_event = el.top()
        popped_event = el.pop()
        assert top_event == popped_event
