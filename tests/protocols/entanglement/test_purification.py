import numpy
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.purification import *
from sequence.topology.node import Node

numpy.random.seed(0)


class FakeNode(Node):
    def __init__(self, name, tl, **kwargs):
        Node.__init__(self, name, tl)
        self.msg_log = None

    def receive_message(self, src: str, msg: Message):
        self.msg_log = [self.timeline.now(), src, msg]


def test_BBPSSWMessage():
    # PING message
    msg = BBPSSWMessage("PING", index=1, kept_memo_r=0, meas_memo_r=1, kept_memo_s=10, meas_memo_s=11)
    assert str(msg) == "BBPSSW Message: msg_type: PING; round #: 1; kept memo id (receiver): 0; " \
                       "measured memo id (receiver): 1; kept memo id (sender): 10; measured memo id (sender): 11;"
    # PONG message
    msg = BBPSSWMessage("PONG", index=1, fidelity=0.9, kept_memo_r=0, meas_memo_r=1)
    assert str(msg) == "BBPSSW Message: msg_type: PONG; round #: 1; kept memo id (receiver): 0; " \
                       "measured memo id (receiver): 1; fidelity: 0.90"


def test_BBPSSW_init():
    tl = Timeline()
    a1 = Node("a1", tl)
    ep = BBPSSW(a1, 0.9)
    assert ep in a1.protocols
    assert ep.threshold == 0.9
    ep.init()


def test_BBPSSW_set_valid_memories():
    tl = Timeline()
    a1 = Node("a1", tl)
    ep = BBPSSW(a1, 0.9)
    ep.set_valid_memories(set(range(10)))
    assert ep.valid_memories == set(range(10))


def test_BBPSSW_pop():
    class Parent():
        def __init__(self):
            self.last_pop = []

        def pop(self, **kwargs):
            self.last_pop = [kwargs["memory_index"], kwargs["another_node"]]

    tl = Timeline()
    a1 = Node("a1", tl)
    ep = BBPSSW(a1, 0.9)
    ep.set_valid_memories(set(range(10)))

    # out of scope memory
    assert ep.pop(memory_index=100, another_node="a0") is False

    # qualified memory
    parent = Parent()
    ep.upper_protocols.append(parent)
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    a1.assign_component(ma, "MemoryArray")
    ma[0].fidelity = 0.99
    ep.pop(memory_index=0, another_node="a0")
    assert parent.last_pop == [0, "a0"]

    # unqualified one memory
    ma[1].fidelity = 0.8
    assert ep.pop(memory_index=1, another_node="a0") is True
    assert ep.purified_lists["a0"][0] == [1]

    ma[2].fidelity = 0.8
    assert ep.pop(memory_index=2, another_node="a2") is True
    assert ep.purified_lists["a0"][0] == [1] and ep.purified_lists["a2"][0] == [2]


def test_BBPSSW_start_round():
    tl = Timeline()
    a1 = Node("a1", tl)
    ep = BBPSSW(a1, 0.9)
    ep.set_valid_memories(set(range(10)))
    ep.purified_lists["a2"] = [[]]
    ep.purified_lists["a2"][0] = [0, 1]

    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    a1.assign_component(ma, "MemoryArray")
    ma[0].fidelity = ma[1].fidelity = 0.8
    ma[0].entangled_memory = {"memo_id": 10}
    ma[1].entangled_memory = {"memo_id": 11}

    a2 = FakeNode("a2", tl)
    cc = ClassicalChannel("cc", tl, 2e-4, 1e3)
    cc.set_ends(a1, a2)

    ep.start_round(0, "a2")
    res = set()
    res.add((1, 0))
    assert ep.waiting_list[0] == res
    tl.run()
    assert a2.msg_log[0] == cc.delay and a2.msg_log[1] == a1.name
    assert a2.msg_log[2].index == 0 and a2.msg_log[2].kept_memo_r == 11 and a2.msg_log[2].meas_memo_r == 10 \
           and a2.msg_log[2].kept_memo_s == 1 and a2.msg_log[2].meas_memo_s == 0


def test_BBPSSW_received_message():
    tl = Timeline()
    a1 = Node("a1", tl)
    ep = BBPSSW(a1, 0.9)
    ep.set_valid_memories(set(range(10)))
    ep.purified_lists["a2"] = [[0, 1]]

    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    a1.assign_component(ma, "MemoryArray")
    ma[0].fidelity = ma[1].fidelity = 0.8
    ma[0].entangled_memory = {"memo_id": 10}
    ma[1].entangled_memory = {"memo_id": 11}

    a2 = FakeNode("a2", tl)
    cc = ClassicalChannel("cc", tl, 2e-4, 1e3)
    cc.set_ends(a1, a2)

    # message from unknown node
    assert ep.received_message("unknown", BBPSSWMessage("PING", index=None, kept_memo_r=None,
                                                        meas_memo_r=None, kept_memo_s=None, meas_memo_s=None)) is False

    # PING message
    msg = BBPSSWMessage("PING", index=0, kept_memo_r=0, meas_memo_r=1, kept_memo_s=10, meas_memo_s=11)
    ep.received_message("a2", msg)
    assert 0 not in ep.purified_lists["a2"][0] and 1 not in ep.purified_lists["a2"][0]
    assert 0 in ep.purified_lists["a2"][1]
    tl.run()
    assert a2.msg_log[0] == cc.delay and a2.msg_log[1] == a1.name
    assert a2.msg_log[2].index == 0 and a2.msg_log[2].fidelity - 0.84 < 0.01 \
           and a2.msg_log[2].kept_memo_r == 10 and a2.msg_log[2].meas_memo_r == 11

    # PONG message
    tl = Timeline()
    a1 = Node("a1", tl)
    ep = BBPSSW(a1, 0.9)
    ep.set_valid_memories(set(range(10)))
    ep.purified_lists["a2"] = [[]]
    ep.waiting_list[0] = set()
    ep.waiting_list[0].add((0, 1))
    ep.waiting_list[0].add((2, 3))

    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    a1.assign_component(ma, "MemoryArray")
    ma[0].fidelity = ma[1].fidelity = 0.8
    ma[0].entangled_memory = {"memo_id": 10}
    ma[1].entangled_memory = {"memo_id": 11}

    a2 = FakeNode("a2", tl)
    cc = ClassicalChannel("cc", tl, 2e-4, 1e3)
    cc.set_ends(a1, a2)

    msg = BBPSSWMessage("PONG", index=0, fidelity=0.88, kept_memo_r=0, meas_memo_r=1)
    ep.received_message("a2", msg)
    assert ma[0].fidelity == 0.88 and 0 in ep.purified_lists["a2"][1]


def test_BBPSSW_purification():
    assert False


def test_BBPSSW_update():
    assert False


def test_BBPSSW_success_probability():
    assert False


def test_improved_fidelity():
    assert False
