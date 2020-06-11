import numpy
import pytest
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.purification import *
from sequence.topology.node import Node

numpy.random.seed(0)


class FakeResourceManager():
    def __init__(self, owner):
        self.log = []

    def update(self, protocol, memory, state):
        self.log.append((memory, state))
        if state == "RAW":
            memory.reset()

class FakeNode(Node):
    def __init__(self, name, tl, **kwargs):
        Node.__init__(self, name, tl)
        self.msg_log = []
        self.resource_manager = FakeResourceManager(self)

    def receive_message(self, src: str, msg: "Message"):
        self.msg_log.append((self.timeline.now(), src, msg))
        for protocol in self.protocols:
            if protocol.name == msg.receiver:
                protocol.received_message(src, msg)


def test_BBPSSWMessage():
    msg = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, "another")
    assert msg.msg_type == BBPSSWMsgType.PURIFICATION_RES
    assert msg.receiver == "another"
    with pytest.raises(Exception):
        BBPSSWMessage("unknown type")


def test_BBPSSW1():
    tl = Timeline()
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    cc = ClassicalChannel("cc", tl, 0, 1e5)
    cc.delay = 1e9
    cc.set_ends(a1, a2)

    tl.init()
    for i in range(1000):
        fidelity = numpy.random.uniform(0.5, 1)
        kept_memo1 = Memory("a1.kept", tl, fidelity=fidelity, frequency=0, efficiency=1, coherence_time=1,
                            wavelength=500)
        kept_memo2 = Memory("a2.kept", tl, fidelity, 0, 1, 1, 500)
        meas_memo1 = Memory("a1.meas", tl, fidelity, 0, 1, 1, 500)
        meas_memo2 = Memory("a2.meas", tl, fidelity, 0, 1, 1, 500)

        kept_memo1.entangled_memory["node_id"] = "a2"
        kept_memo1.entangled_memory["memo_id"] = "a2.kept"
        kept_memo2.entangled_memory["node_id"] = "a1"
        kept_memo2.entangled_memory["memo_id"] = "a1.kept"
        meas_memo1.entangled_memory["node_id"] = "a2"
        meas_memo1.entangled_memory["memo_id"] = "a2.meas"
        meas_memo2.entangled_memory["node_id"] = "a1"
        meas_memo2.entangled_memory["memo_id"] = "a1.meas"

        ep1 = BBPSSW(a1, "a1.ep1.%d" % i, kept_memo1, meas_memo1)
        ep2 = BBPSSW(a2, "a2.ep2.%d" % i, kept_memo2, meas_memo2)
        a1.protocols.append(ep1)
        a2.protocols.append(ep2)
        ep1.set_others(ep2)
        ep2.set_others(ep1)

        ep1.start()
        ep2.start()

        assert ep1.is_success == ep2.is_success

        tl.run()

        assert a1.resource_manager.log[-2] == (meas_memo1, "RAW")
        assert a2.resource_manager.log[-2] == (meas_memo2, "RAW")
        assert meas_memo1.fidelity == meas_memo2.fidelity == meas_memo1.raw_fidelity

        if ep1.is_success:
            assert kept_memo1.fidelity == kept_memo2.fidelity == BBPSSW.improved_fidelity(fidelity)
            assert kept_memo1.entangled_memory["node_id"] == "a2" and kept_memo2.entangled_memory["node_id"] == "a1"
            assert a1.resource_manager.log[-1] == (kept_memo1, "ENTANGLED")
            assert a2.resource_manager.log[-1] == (kept_memo2, "ENTANGLED")
        else:
            assert kept_memo1.fidelity == kept_memo2.fidelity == kept_memo1.raw_fidelity
            assert kept_memo1.entangled_memory["node_id"] == kept_memo2.entangled_memory["node_id"] == None
            assert a1.resource_manager.log[-1] == (kept_memo1, "RAW")
            assert a2.resource_manager.log[-1] == (kept_memo2, "RAW")


def test_BBPSSW2():
    tl = Timeline()
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    cc = ClassicalChannel("cc", tl, 0, 1e5)
    cc.delay = 1e9
    cc.set_ends(a1, a2)

    tl.init()
    counter1 = counter2 = 0
    fidelity = 0.8

    for i in range(1000):
        kept_memo1 = Memory("a1.kept", tl, fidelity=fidelity, frequency=0, efficiency=1, coherence_time=1,
                            wavelength=500)
        kept_memo2 = Memory("a2.kept", tl, fidelity, 0, 1, 1, 500)
        meas_memo1 = Memory("a1.meas", tl, fidelity, 0, 1, 1, 500)
        meas_memo2 = Memory("a2.meas", tl, fidelity, 0, 1, 1, 500)

        kept_memo1.entangled_memory["node_id"] = "a2"
        kept_memo1.entangled_memory["memo_id"] = "a2.kept"
        kept_memo2.entangled_memory["node_id"] = "a1"
        kept_memo2.entangled_memory["memo_id"] = "a1.kept"
        meas_memo1.entangled_memory["node_id"] = "a2"
        meas_memo1.entangled_memory["memo_id"] = "a2.meas"
        meas_memo2.entangled_memory["node_id"] = "a1"
        meas_memo2.entangled_memory["memo_id"] = "a1.meas"

        ep1 = BBPSSW(a1, "a1.ep1.%d" % i, kept_memo1, meas_memo1)
        ep2 = BBPSSW(a2, "a2.ep2.%d" % i, kept_memo2, meas_memo2)
        a1.protocols.append(ep1)
        a2.protocols.append(ep2)
        ep1.set_others(ep2)
        ep2.set_others(ep1)

        ep1.start()
        ep2.start()

        assert ep1.is_success == ep2.is_success
        if ep1.is_success:
            counter1 += 1
        else:
            counter2 += 1

        tl.run()

    assert abs(counter1 / (counter1 + counter2) - BBPSSW.success_probability(fidelity)) < 0.1
