from math import inf
from numpy import random

from sequence.kernel.entity import Entity
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline

_DEFAULT_DUMMY_NAME = 'dummy'
_INITIAL_COUNT = 0


class Dummy(Entity):
    def __init__(self, name, timeline):
        Entity.__init__(self, name, timeline)
        self.initialized = False
        self.counter = _INITIAL_COUNT
        self.click_time = None

    def init(self):
        self.initialized = True

    def operate(self):
        self.counter += 1

    def click(self):
        self.click_time = self.timeline.now()


def test_init():
    timeline = Timeline()
    dummy = Dummy(_DEFAULT_DUMMY_NAME, timeline)

    assert not dummy.initialized

    timeline.init()

    assert dummy.initialized


def _set_up_test(activation_method: str, stop_time = inf, number_of_dummys: int = 1, event_time: int = 10, event_priority = inf) -> Timeline:
    timeline = Timeline(stop_time)
    dummys = [Dummy(f'{dummy_number}', timeline) for dummy_number in range(number_of_dummys)]
    processes = [Process(dummy, activation_method, []) for dummy in dummys]
    events = [Event(event_time, process, event_priority) for process in processes]

    for event in events:
        timeline.schedule(event)

    timeline.init()

    return timeline, dummys, events


def test_run():
    random.seed(0)
    time = random.randint(0, 20)
    priority = random.randint(0, 20)
    timeline, [dummy], _ = _set_up_test('operate', event_time=time, event_priority=priority)

    timeline.run()

    assert dummy.counter == 1
    assert timeline.now() == timeline.time == time and len(timeline.events) == _INITIAL_COUNT


def test_run_with_stop_time():
    random.seed(0)
    stop_time = 5
    time = random.randint(0, 20)
    priority = random.randint(0, 20)
    timeline, [dummy], events = _set_up_test('operate', stop_time, event_time=time, event_priority=priority)

    timeline.run()

    assert dummy.counter == _INITIAL_COUNT
    assert timeline.now() == timeline.time < stop_time and len(timeline.events) == len(events)
    

def test_remove_event():
    timeline, dummys, events = _set_up_test('operate', number_of_dummys=2, event_time=1)

    assert all(dummy.counter == _INITIAL_COUNT for dummy in dummys)

    timeline.remove_event(events[0])
    timeline.run()

    assert dummys[0].counter == _INITIAL_COUNT and dummys[1].counter == 1


def test_update_event_time():
    timeline, dummys, events = _set_up_test('click', number_of_dummys=2)

    assert all(dummy.click_time is None for dummy in dummys)

    timeline.update_event_time(events[1], 20)
    timeline.run()

    assert dummys[0].click_time == 10 and dummys[1].click_time == 20


def test_ns_to_human_time():
    tl = Timeline()
    ten_hours = int(10 * 3600e9)
    assert tl.ns_to_human_time(ten_hours) == "10:00:00"
    ten_minutes = int(600e9)
    assert tl.ns_to_human_time(ten_minutes) == "0:10:00"
    ten_seconds = int(1e10)
    assert tl.ns_to_human_time(ten_seconds) == "0:00:10"
    ten_ms = int(1e7)
    assert tl.ns_to_human_time(ten_ms) == "0:00:00.010000"


def test_remove_entity_by_name():
    tl = Timeline()
    e1 = Dummy("e1", tl)
    assert "e1" in tl.entities
    assert e1.timeline == tl
    tl.remove_entity_by_name("e1")
    assert not "e1" in tl.entities
    assert e1.timeline is None


def test_get_entity_by_name():
    tl = Timeline()
    e1 = Dummy("e1", tl)
    assert tl.get_entity_by_name("e1") == e1
    assert tl.get_entity_by_name("e2") is None


def test_schedule():
    ENTITY_NAME = "dummy"
    SCHEDULE_NUM = 100

    tl = Timeline()
    e1 = Dummy(ENTITY_NAME, tl)

    for i in range(SCHEDULE_NUM):
        if i % 2:
            # schedule event by entity object
            tl.schedule(Event(0, Process(e1, "operate", [])))
        else:
            # schedule event by entity name
            tl.schedule(Event(0, Process(ENTITY_NAME, "operate", [])))
    assert tl.schedule_counter == SCHEDULE_NUM
    tl.init()
    tl.run()
    assert tl.run_counter == SCHEDULE_NUM == e1.counter
