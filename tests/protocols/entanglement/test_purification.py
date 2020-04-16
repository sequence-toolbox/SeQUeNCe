import numpy
import pytest
from sequence.components.memory import AtomMemory
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.purification import *
from sequence.topology.node import Node

numpy.random.seed(0)


class ResourceManager():
    def __init__(self):
        self.log = []

    def update(self, protocol, memory, state):
        self.log.append((memory, state))


class FakeNode(Node):
    def __init__(self, name, tl, **kwargs):
        Node.__init__(self, name, tl)
        self.msg_log = []
        self.resource_manager = ResourceManager()

    def receive_message(self, src: str, msg: "Message"):
        self.msg_log.append((self.timeline.now(), src, msg))
        for protocol in self.protocols:
            if protocol.name == msg.receiver:
                protocol.received_message(src, msg)


def test_BBPSSWMessage():
    msg = BBPSSWMessage("PURIFICATION_RES", "another")
    assert msg.msg_type == "PURIFICATION_RES" and msg.receiver == "another"
    with pytest.raises(Exception):
        BBPSSWMessage("unknown type")


def test_BBPSSW():
    tl = Timeline()
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    cc = ClassicalChannel("cc", tl, 0, 1e5)
    cc.delay = 1e9
    cc.set_ends(a1, a2)

    tl.init()
    for i in range(1000):
        fidelity = numpy.random.uniform(0.5, 1)
        kept_memo1 = AtomMemory("a1.kept", tl, fidelity=fidelity)
        kept_memo2 = AtomMemory("a2.kept", tl, fidelity=fidelity)
        meas_memo1 = AtomMemory("a1.meas", tl, fidelity=fidelity)
        meas_memo2 = AtomMemory("a2.meas", tl, fidelity=fidelity)

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
        ep1.set_another(ep2)
        ep2.set_another(ep1)

        ep1.start()
        ep2.start()

        assert ep1.is_success == ep2.is_success
        assert a1.resource_manager.log[-1] == (meas_memo1, "EMPTY")
        assert a2.resource_manager.log[-1] == (meas_memo2, "EMPTY")
        assert meas_memo1.fidelity == meas_memo2.fidelity == 0

        tl.run()

        if ep1.is_success:
            assert kept_memo1.fidelity == kept_memo2.fidelity == BBPSSW.improved_fidelity(fidelity)
            assert kept_memo1.entangled_memory["node_id"] == "a2" and kept_memo2.entangled_memory["node_id"] == "a1"
            assert a1.resource_manager.log[-1] == (kept_memo1, "ENTANGLE")
            assert a2.resource_manager.log[-1] == (kept_memo2, "ENTANGLE")
        else:
            assert kept_memo1.fidelity == kept_memo2.fidelity == 0
            assert kept_memo1.entangled_memory["node_id"] == kept_memo2.entangled_memory["node_id"] == None
            assert a1.resource_manager.log[-1] == (kept_memo1, "EMPTY")
            assert a2.resource_manager.log[-1] == (kept_memo2, "EMPTY")
