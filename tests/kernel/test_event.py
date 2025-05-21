import math

from sequence.kernel.event import Event
from sequence.kernel.process import Process


class NopOwner:
    def action(self):
        pass


nop_process = Process(NopOwner(), "action", [])


def test_event():
    e1 = Event(0, nop_process)
    assert e1.time == 0 and e1.priority == math.inf
    e2 = Event(5, nop_process)
    assert e2.time == 5 and e2.priority == math.inf
    e3 = Event(5, nop_process, 1)
    assert e3.time == 5 and e3.priority == 1
    assert e1 < e2
    assert e1 < e3
    assert e3 < e2
