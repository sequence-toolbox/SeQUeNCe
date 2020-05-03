from numpy import random

random.seed(0)

from sequence.protocols.network.rsvp import MemoryTimeCard, Reservation


def test_MemoryTimeCard_add():
    timecard = MemoryTimeCard(0)
    r1 = Reservation("", "", 10, 20, 5)
    assert timecard.add(r1) is True
    r2 = Reservation("", "", 5, 7, 5)
    assert timecard.add(r2) is True
    r3 = Reservation("", "", 20, 25, 5)
    assert timecard.add(r3) is False
    r4 = Reservation("", "", 15, 25, 5)
    assert timecard.add(r4) is False


def test_MemoryTimeCard_remove():
    timecard = MemoryTimeCard(0)
    r1 = Reservation("", "", 10, 20, 5)
    r2 = Reservation("", "", 5, 7, 5)
    timecard.add(r1)
    assert timecard.remove(r2) is False
    assert timecard.remove(r1) is True


def test_MemoryTimeCard_schedule_reservation():
    timecard = MemoryTimeCard(0)
    for _ in range(500):
        s_time = random.randint(100)
        r = Reservation("", "", s_time, s_time + random.randint(24) + 1, 1)
        timecard.add(r)

    for i, r in enumerate(timecard.reservations):
        if i > 0:
            assert timecard.reservations[i - 1].end_time < r.start_time
