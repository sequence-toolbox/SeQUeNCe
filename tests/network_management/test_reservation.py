from numpy import random
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.components.memory import MemoryArray
from sequence.kernel.timeline import Timeline
from sequence.network_management.reservation import *

random.seed(0)

from sequence.network_management.reservation import MemoryTimeCard, Reservation
from sequence.entanglement_management.swapping import EntanglementSwappingA
from sequence.topology.node import QuantumRouter, BSMNode


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
    def __init__(self, name, timeline, memo_size=50):
        super().__init__(name, timeline, memo_size)

        memo_arr_name = ""
        for name in self.components.keys():
            if type(self.components[name]) is MemoryArray:
                memo_arr_name = name
                break

        self.rsvp = ResourceReservationProtocol(self, self.name + ".rsvp", memo_arr_name)
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

    memo_arr = None
    for c in n1.components.values():
        if type(c) is MemoryArray:
            memo_arr = c
            break

    assert len(n1.rsvp.timecards) == len(memo_arr)
    n1.rsvp.push("n10", 1, 10, 1000, 0.9)
    assert n1.pop_log[0]["msg"].msg_type == RSVPMsgType.REJECT
    assert len(n1.push_log) == 0
    n1.rsvp.push("n10", 1, 10, 50, 0.9)
    assert n1.push_log[0]["msg"].msg_type == RSVPMsgType.REQUEST
    assert len(n1.pop_log) == 1
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 1
    n1.rsvp.push("n10", 5, 10, 1, 0.9)
    assert n1.pop_log[1]["msg"].msg_type == RSVPMsgType.REJECT
    assert len(n1.push_log) == 1
    n1.rsvp.push("n10", 20, 30, 1, 0.9)
    assert n1.push_log[1]["msg"].msg_type == RSVPMsgType.REQUEST
    assert len(n1.pop_log) == 2


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
    msg = ResourceReservationMessage(RSVPMsgType.REQUEST, n1.rsvp.name, reservation)
    msg.qcaps.append(QCap("n0"))
    n1.rsvp.pop("n0", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n2"
    assert n1.push_log[0]["msg"].msg_type == RSVPMsgType.REQUEST
    assert len(n1.push_log[0]["msg"].qcaps) == 2
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 1
    reset(n1)

    # responder receives REQUEST and approve it
    reservation = Reservation("n0", "n1", 1, 10, 50, 0.9)
    msg = ResourceReservationMessage(RSVPMsgType.REQUEST, n1.rsvp.name, reservation)
    msg.qcaps.append(QCap("n0"))
    n1.rsvp.pop("n0", msg)
    assert len(n1.pop_log) == 1 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n0"
    assert n1.push_log[0]["msg"].msg_type == RSVPMsgType.APPROVE
    assert len(n1.push_log[0]["msg"].path) == 2
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 1
    reset(n1)

    # node receives REQUEST and reject it
    reservation = Reservation("n0", "n2", 1, 10, 1000, 0.9)
    msg = ResourceReservationMessage(RSVPMsgType.REQUEST, n1.rsvp.name, reservation)
    msg.qcaps.append(QCap("n0"))
    n1.rsvp.pop("n0", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n0"
    assert n1.push_log[0]["msg"].msg_type == RSVPMsgType.REJECT
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
    msg = ResourceReservationMessage(RSVPMsgType.REJECT, n1.rsvp.name,
                                     reservation, path=['n1', 'n2'])
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 1 and len(n1.push_log) == 0
    assert n1.pop_log[0]["msg"].msg_type == RSVPMsgType.REJECT
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
    msg = ResourceReservationMessage(RSVPMsgType.REJECT, n1.rsvp.name,
                                     reservation, path=['n0', 'n1', 'n2'])
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["msg"].msg_type == RSVPMsgType.REJECT
    for card in n1.rsvp.timecards:
        assert len(card.reservations) == 0
    reset(n1)

    # initiator receives APPROVE
    reservation = Reservation("n1", "n2", 1, 10, 1000, 0.9)
    msg = ResourceReservationMessage(RSVPMsgType.APPROVE, n1.rsvp.name,
                                     reservation, path=["n1", "n2"])
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 1 and len(n1.push_log) == 0
    assert n1.pop_log[0]["msg"].msg_type == RSVPMsgType.APPROVE
    reset(n1)

    # intermediate node receives APPROVE
    reservation = Reservation("n0", "n2", 1, 10, 1000, 0.9)
    msg = ResourceReservationMessage(RSVPMsgType.APPROVE, n1.rsvp.name, reservation, path=["n0", "n1", "n2"])
    n1.rsvp.pop("n2", msg)
    assert len(n1.pop_log) == 0 and len(n1.push_log) == 1
    assert n1.push_log[0]["dst"] == "n0" and n1.push_log[0]["msg"].msg_type == RSVPMsgType.APPROVE
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
        router = FakeNode("r%d" % i, tl, memo_size=20)
        routers.append(router)
    for i in range(4):
        mid = BSMNode("mid%d" % i, tl, [routers[i].name, routers[i + 1].name])
        mids.append(mid)
    for i in range(4):
        qc = QuantumChannel("qc_l_%d" % i, tl, 0, 100)
        qc.set_ends(routers[i], mids[i].name)
        routers[i].add_bsm_node(mids[i].name, routers[i + 1].name)
        qc = QuantumChannel("qc_r_%d" % i, tl, 0, 100)
        qc.set_ends(routers[i + 1], mids[i].name)
        routers[i + 1].add_bsm_node(mids[i].name, routers[i].name)
    # all-to-all classical connections
    for i, n1 in enumerate(routers + mids):
        for j, n2 in enumerate(routers + mids):
            if i == j:
                continue
            cc = ClassicalChannel("cc_%s_%s" % (n1.name, n2.name), tl, 10, delay=1e6)
            cc.set_ends(n1, n2.name)

    tl.init()

    path = [r.name for r in routers]
    reservation = Reservation("r0", "r4", 1, int(1e9), 10, 0.9)

    for node in [routers[0], routers[-1]]:
        for i, card in enumerate(node.rsvp.timecards):
            if i >= 10:
                break
            card.add(reservation)

        rules = node.rsvp.create_rules(path, reservation)
        assert len(rules) == 3
        node.rsvp.load_rules(rules, reservation)

    for node in routers[1:-1]:
        for i, card in enumerate(node.rsvp.timecards):
            card.add(reservation)
        rules = node.rsvp.create_rules(path, reservation)
        assert len(rules) == 6
        node.rsvp.load_rules(rules, reservation)

    tl.run()
    for node in routers:
        assert len(node.resource_manager.rule_manager) == 0

    memo_arr = None
    for c in routers[0].components.values():
        if type(c) is MemoryArray:
            memo_arr = c
            break

    counter = 0
    for memory in memo_arr:
        print(memory.entangled_memory["node_id"], memory.fidelity)
        if memory.entangled_memory["node_id"] == "r4" and memory.fidelity >= 0.9:
            counter += 1
    assert counter >= 0

    for info in routers[0].resource_manager.memory_manager:
        if info.state == "ENTANGLED" \
                and info.remote_node == "r4" \
                and info.fidelity >= 0.9:
            counter -= 1
    assert counter == 0


def test_ResourceReservationProtocol_set_es_params():
    class TestNode(FakeNode):
        def __init__(self, name, tl):
            super().__init__(name, tl, memo_size=20)
            self.counter = 0

        def receive_message(self, src: str, msg: "Message") -> None:
            for protocol in self.resource_manager.pending_protocols:
                if isinstance(protocol, EntanglementSwappingA):
                    assert protocol.success_prob == 0.8 and protocol.degradation == 0.7
                    self.counter += 1
            super().receive_message(src, msg)

    tl = Timeline()
    routers = []
    mids = []
    for i in range(5):
        router = TestNode("r%d" % i, tl)
        router.set_seed(i)
        router.rsvp.set_swapping_success_rate(0.8)
        router.rsvp.set_swapping_degradation(0.7)
        routers.append(router)
    for i in range(4):
        mid = BSMNode("mid%d" % i, tl, [routers[i].name, routers[i + 1].name])
        mid.set_seed(i + 5)
        mids.append(mid)
    for i in range(4):
        qc = QuantumChannel("qc_l_%d" % i, tl, 0, 100)
        qc.set_ends(routers[i], mids[i].name)
        routers[i].add_bsm_node(mids[i].name, routers[i + 1].name)
        qc = QuantumChannel("qc_r_%d" % i, tl, 0, 100)
        qc.set_ends(routers[i + 1], mids[i].name)
        routers[i + 1].add_bsm_node(mids[i].name, routers[i].name)
    # all-to-all classical connections
    for i, n1 in enumerate(routers + mids):
        for j, n2 in enumerate(routers + mids):
            if i == j:
                continue
            cc = ClassicalChannel("cc_%s_%s" % (n1.name, n2.name), tl, 10, delay=100000)
            cc.set_ends(n1, n2.name)

    tl.init()

    path = [r.name for r in routers]
    reservation = Reservation("r0", "r4", 1, 20000000, 10, 0.9)
    for node in [routers[0], routers[-1]]:
        for i, card in enumerate(node.rsvp.timecards):
            if i >= 10:
                break
            card.add(reservation)

        rules = node.rsvp.create_rules(path, reservation)
        assert len(rules) == 3
        node.rsvp.load_rules(rules, reservation)

    for node in routers[1:-1]:
        for i, card in enumerate(node.rsvp.timecards):
            card.add(reservation)
        rules = node.rsvp.create_rules(path, reservation)
        assert len(rules) == 6
        node.rsvp.load_rules(rules, reservation)

    tl.run()
    counter = 0
    for node in routers:
        counter += node.counter
    assert counter > 0
