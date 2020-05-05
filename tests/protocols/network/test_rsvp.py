from numpy import random
from sequence.components.optical_channel import QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.network.rsvp import ResourceReservationProtocol, ResourceReservationMessage, QCap

random.seed(0)

from sequence.protocols.network.rsvp import MemoryTimeCard, Reservation
from sequence.topology.node import QuantumRouter, MiddleNode


def test_MemoryTimeCard_add():
    timecard = MemoryTimeCard(0)
    r1 = Reservation("", "", 10, 20, 5, 0.9)
    assert timecard.add(r1) is True
    r2 = Reservation("", "", 5, 7, 5, 0.9)
    assert timecard.add(r2) is True
    r3 = Reservation("", "", 20, 25, 5, 0.9)
    assert timecard.add(r3) is False
    r4 = Reservation("", "", 15, 25, 5, 0.9)
    assert timecard.add(r4) is False


def test_MemoryTimeCard_remove():
    timecard = MemoryTimeCard(0)
    r1 = Reservation("", "", 10, 20, 5, 0.9)
    r2 = Reservation("", "", 5, 7, 5, 0.9)
    timecard.add(r1)
    assert timecard.remove(r2) is False
    assert timecard.remove(r1) is True


def test_MemoryTimeCard_schedule_reservation():
    timecard = MemoryTimeCard(0)
    for _ in range(500):
        s_time = random.randint(100)
        r = Reservation("", "", s_time, s_time + random.randint(24) + 1, 1, 0.9)
        timecard.add(r)

    for i, r in enumerate(timecard.reservations):
        if i > 0:
            assert timecard.reservations[i - 1].end_time < r.start_time


class FakeNode(QuantumRouter):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.rsvp = ResourceReservationProtocol(self, self.name + ".rsvp")
        self.rsvp.upper_protocols.append(self)
        self.rsvp.lower_protocols.append(self)
        self.push_log = []
        self.pop_log = []

    def receive_message(self, src: str, msg: "Message") -> None:
        if msg.receiver == "network_manager":
            self.network_manager.received_message(src, msg)
        else:
            super().receive_message(src, msg)

    def push(self, **kwargs):
        self.push_log.append(kwargs)

    def pop(self, **kwargs):
        self.pop_log.append(kwargs)


def test_ResourceReservationProtocol_push():
    tl = Timeline()
    n1 = FakeNode("n1", tl)
    assert len(n1.rsvp.timecards) == len(n1.memory_array)
    n1.rsvp.push("n10", 1, 10, 1000, 0.9)
    assert n1.pop_log[0]["msg"].msg_type == "REJECT" and len(n1.push_log) == 0
    n1.rsvp.push("n10", 1, 10, 50, 0.9)
    assert n1.push_log[0]["msg"].msg_type == "REQUEST" and len(n1.pop_log) == 1
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 1
    n1.rsvp.push("n10", 5, 10, 1, 0.9)
    assert n1.pop_log[1]["msg"].msg_type == "REJECT" and len(n1.push_log) == 1
    n1.rsvp.push("n10", 20, 30, 1, 0.9)
    assert n1.push_log[1]["msg"].msg_type == "REQUEST" and len(n1.pop_log) == 2


def test_ResourceReservationProtocol_pop():
    def reset(node):
        for card in node.rsvp.timecards:
            card.remove(reservation)
        node.push_log = []
        node.pop_log = []

    tl = Timeline()
    n1 = FakeNode("n1", tl)
    n1.map_to_middle_node["n0"] = "m0"
    n1.map_to_middle_node["n2"] = "m1"

    # intermediate node receives REQUEST and approve it
    reservation = Reservation("n0", "n2", 1, 10, 25, 0.9)
    msg = ResourceReservationMessage("REQUEST", n1.rsvp.name, reservation)
    msg.qcaps.append(QCap("n0"))
    n1.rsvp.pop("n0", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n2" and n1.push_log[0]["msg"].msg_type == "REQUEST"
    assert len(n1.push_log[0]["msg"].qcaps) == 2
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 1
    reset(n1)

    # responder receives REQUEST and approve it
    reservation = Reservation("n0", "n1", 1, 10, 50, 0.9)
    msg = ResourceReservationMessage("REQUEST", n1.rsvp.name, reservation)
    msg.qcaps.append(QCap("n0"))
    n1.rsvp.pop("n0", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n0" and n1.push_log[0]["msg"].msg_type == "APPROVE"
    assert len(n1.push_log[0]["msg"].path) == 2
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 1
    reset(n1)

    # node receives REQUEST and reject it
    reservation = Reservation("n0", "n2", 1, 10, 1000, 0.9)
    msg = ResourceReservationMessage("REQUEST", n1.rsvp.name, reservation)
    msg.qcaps.append(QCap("n0"))
    n1.rsvp.pop("n0", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n0" and n1.push_log[0]["msg"].msg_type == "REJECT"
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 0
    reset(n1)

    # initiator receives REJECT
    reservation = Reservation("n1", "n2", 1, 10, 10, 0.9)
    for i, card in enumerate(n1.rsvp.timecards):
        if i < 10:
            card.add(reservation)
        else:
            break
    msg = ResourceReservationMessage("REJECT", n1.rsvp.name, reservation)
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 1 and len(n1.push_log) == 0
    assert n1.pop_log[0]["msg"].msg_type == "REJECT"
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 0
    reset(n1)

    # intermediate node receives REJECT
    reservation = Reservation("n0", "n2", 1, 10, 10, 0.9)
    for i, card in enumerate(n1.rsvp.timecards):
        if i < 10:
            card.add(reservation)
        else:
            break
    msg = ResourceReservationMessage("REJECT", n1.rsvp.name, reservation)
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["msg"].msg_type == "REJECT"
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 0
    reset(n1)

    # initiator receives APPROVE
    reservation = Reservation("n1", "n2", 1, 10, 1000, 0.9)
    msg = ResourceReservationMessage("APPROVE", n1.rsvp.name, reservation, path=["n1", "n2"])
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 1 and len(n1.push_log) == 0
    assert n1.pop_log[0]["msg"].msg_type == "APPROVE"
    reset(n1)

    # intermediate node receives APPROVE
    reservation = Reservation("n0", "n2", 1, 10, 1000, 0.9)
    msg = ResourceReservationMessage("APPROVE", n1.rsvp.name, reservation, path=["n0", "n1", "n2"])
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n0" and n1.push_log[0]["msg"].msg_type == "APPROVE"
    reset(n1)


def test_ResourceReservationProtocol_schedule():
    tl = Timeline()
    n1 = FakeNode("n1", tl)
    for _ in range(1000):
        s_time = random.randint(1000)
        memo_size = random.randint(25) + 1
        reservation = Reservation("", "", s_time, s_time + 1 + random.randint(200), memo_size, 0.9)
        if n1.rsvp.schedule(reservation):
            counter = 0
            for card in n1.rsvp.timecards:
                if reservation in card.reservations:
                    counter += 1
            assert counter == memo_size * 2
        else:
            counter = 0
            for card in n1.rsvp.timecards:
                if reservation in card.reservations:
                    counter += 1
            assert counter == 0

    n2 = FakeNode("n2", tl)
    for _ in range(1000):
        s_time = random.randint(1000)
        memo_size = random.randint(25) + 1
        reservation = Reservation("n2", "", s_time, s_time + 1 + random.randint(200), memo_size, 0.9)
        if n2.rsvp.schedule(reservation):
            counter = 0
            for card in n2.rsvp.timecards:
                if reservation in card.reservations:
                    counter += 1
            assert counter == memo_size
        else:
            counter = 0
            for card in n2.rsvp.timecards:
                if reservation in card.reservations:
                    counter += 1
            assert counter == 0


def test_ResourceReservationProtocol_create_rules():
    tl = Timeline()
    routers = []
    mids = []
    for i in range(5):
        router = FakeNode("r%d" % i, tl)
        routers.append(router)
    for i in range(4):
        mid = MiddleNode("mid%d" % i, tl, [routers[i].name, routers[i + 1].name])
        mids.append(mid)
    for i in range(4):
        qc = QuantumChannel("qc_l_%d" % i, tl, 0, 100)
        qc.set_ends(routers[i], mids[i])
        qc = QuantumChannel("qc_r_%d" % i, tl, 0, 100)
        qc.set_ends(routers[i + 1], mids[i])

    tl.init()

    path = [r.name for r in routers]
    reservation = Reservation("r0", "r4", 0, 100000, 25, 0.9)

    for node in [routers[0], routers[-1]]:
        for i, card in enumerate(node.rsvp.timecards):
            if i >= 25:
                break
            card.add(reservation)

        rules = node.rsvp.create_rules(path, reservation)
        assert len(rules) == 3

    for node in routers[1:-1]:
        for i, card in enumerate(node.rsvp.timecards):
            card.add(reservation)
        rules = node.rsvp.create_rules(path, reservation)
        assert len(rules) == 6
