# test_dqc_node.py
from typing import Optional

import pytest

from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.components.memory import MemoryArray
from sequence.components.photon import Photon

from sequence.topology.node import DQCNode 


def test_DQCNode_init_sets_data_memory():
    tl = Timeline()
    qn = DQCNode("qn1", tl, data_memo_size=4, memo_size=2)

    data_memory_arr_name = qn.data_memo_arr_name

    assert data_memory_arr_name in qn.components
    data_memory_arr = qn.components[data_memory_arr_name]
    assert isinstance(data_memory_arr, MemoryArray)

    if hasattr(data_memory_arr, "memories"):
        assert len(data_memory_arr.memories) == 4
    elif hasattr(data_memory_arr, "size"):
        assert data_memory_arr.size == 4
    else:
        pytest.skip("MemoryArray does not expose size; cannot assert data_memo_size.")


def test_DQCNode_assign_cchannel():
    tl = Timeline()
    qn = DQCNode("qn1", tl, data_memo_size=1)
    cc = ClassicalChannel("cc", tl, 1e3)
    qn.assign_cchannel(cc, "qn2")
    assert "qn2" in qn.cchannels and qn.cchannels["qn2"] == cc


def test_DQCNode_assign_qchannel():
    tl = Timeline()
    qn = DQCNode("qn1", tl, data_memo_size=1)
    qc = QuantumChannel("qc", tl, 2e-4, 1e3)
    qn.assign_qchannel(qc, "qn2")
    assert "qn2" in qn.qchannels and qn.qchannels["qn2"] == qc


def test_DQCNode_send_message_like_Node():
    class FakeQNode(DQCNode):
        def __init__(self, name, tl):
            super().__init__(name, tl, data_memo_size=1, memo_size=1)
            self.log = []

        def receive_message(self, src, msg):
            self.log.append((self.timeline.now(), src, msg))

    tl = Timeline()
    qn1 = FakeQNode("qn1", tl)
    qn2 = FakeQNode("qn2", tl)
    cc0 = ClassicalChannel("cc0", tl, 1e3)
    cc1 = ClassicalChannel("cc1", tl, 1e3)
    cc0.set_ends(qn1, qn2.name)
    cc1.set_ends(qn2, qn1.name)

    MSG_NUM = 10
    CC_DELAY = cc0.delay

    for i in range(MSG_NUM):
        qn1.send_message("qn2", str(i))
        tl.time += 1

    for i in range(MSG_NUM):
        qn2.send_message("qn1", str(i))
        tl.time += 1

    assert len(qn1.log) == len(qn2.log) == 0
    tl.init()
    tl.run()

    expect_qn1_log = [(CC_DELAY + MSG_NUM + i, "qn2", str(i)) for i in range(MSG_NUM)]
    for actual, expect in zip(qn1.log, expect_qn1_log):
        assert actual == expect

    expect_qn2_log = [(CC_DELAY + i, "qn1", str(i)) for i in range(MSG_NUM)]
    for actual, expect in zip(qn2.log, expect_qn2_log):
        assert actual == expect


def test_DQCNode_send_qubit_like_Node():
    import numpy as np
    np.random.seed(0)

    class FakeQNode(DQCNode):
        def __init__(self, name, tl):
            super().__init__(name, tl, data_memo_size=1, memo_size=1)
            self.log = []

        def receive_qubit(self, src, qubit):
            self.log.append((self.timeline.now(), src, qubit.name))

    tl = Timeline()
    qn1 = FakeQNode("qn1", tl)
    qn2 = FakeQNode("qn2", tl)
    qc0 = QuantumChannel("qc0", tl, 2e-4, 2e4)  # loss, delay
    qc1 = QuantumChannel("qc1", tl, 2e-4, 2e4)
    qc0.set_ends(qn1, qn2.name)
    qc1.set_ends(qn2, qn1.name)
    tl.init()

    N = 1000
    for i in range(N):
        photon = Photon(str(i), tl)
        qn1.send_qubit("qn2", photon)
        tl.time += 1

    for i in range(N):
        photon = Photon(str(i), tl)
        qn2.send_qubit("qn1", photon)
        tl.time += 1

    assert len(qn1.log) == len(qn2.log) == 0
    tl.run()

    expect_rate_0 = 1 - qc0.loss
    expect_rate_1 = 1 - qc1.loss
    assert abs(len(qn1.log) / N - expect_rate_1) < 0.1
    assert abs(len(qn2.log) / N - expect_rate_0) < 0.1


# ---- Dispatch behavior specific to DQCNode.receive_message ----

class Sink:
    def __init__(self):
        self.calls = []

    def received_message(self, src, msg):
        self.calls.append((src, msg))


def test_DQCNode_receive_message_dispatch_to_apps_and_managers():
    class SimpleMsg:
        def __init__(self, receiver):
            self.receiver = receiver
            self.protocol_type = None

    tl = Timeline()
    qn = DQCNode("qn", tl, data_memo_size=1, memo_size=1)

    nm = Sink()
    rm = Sink()
    ta = Sink()  # teleport_app
    tda = Sink()  # teledata_app
    tga = Sink()  # telegate_app

    qn.network_manager = nm
    qn.resource_manager = rm
    qn.teleport_app = ta
    qn.teledata_app = tda
    qn.telegate_app = tga

    qn.receive_message("peer", SimpleMsg("network_manager"))
    qn.receive_message("peer", SimpleMsg("resource_manager"))
    qn.receive_message("peer", SimpleMsg("teleport_app"))
    qn.receive_message("peer", SimpleMsg("teledata_app"))
    qn.receive_message("peer", SimpleMsg("telegate_app"))

    assert len(nm.calls) == 1 and nm.calls[0][0] == "peer"
    assert len(rm.calls) == 1 and rm.calls[0][0] == "peer"
    assert len(ta.calls) == 1 and ta.calls[0][0] == "peer"
    assert len(tda.calls) == 1 and tda.calls[0][0] == "peer"
    assert len(tga.calls) == 1 and tga.calls[0][0] == "peer"


def test_DQCNode_receive_message_dispatch_to_named_protocol():
    class SimpleMsg:
        def __init__(self, receiver):
            self.receiver = receiver
            self.protocol_type = None

    class ProtoA:
        def __init__(self, name):
            self.name = name
            self.calls = []

        def received_message(self, src, msg):
            self.calls.append((src, msg))

    tl = Timeline()
    qn = DQCNode("qn", tl, data_memo_size=1, memo_size=1)

    p = ProtoA("protoA")
    qn.protocols.append(p)

    qn.receive_message("peer", SimpleMsg("protoA"))
    assert len(p.calls) == 1
    assert p.calls[0][0] == "peer"


def test_DQCNode_receive_message_dispatch_by_protocol_type_when_receiver_None():
    class SimpleMsg:
        def __init__(self, protocol_type: Optional[str] = None):
            self.receiver = None
            self.protocol_type = protocol_type

    class ProtoTypeA:
        def __init__(self):
            self.name = "pta"
            self.calls = []
            self.protocol_type = "ProtoTypeA"

        def received_message(self, src, msg):
            self.calls.append((src, msg))

    class ProtoTypeB:
        def __init__(self):
            self.name = "ptb"
            self.calls = []
            self.protocol_type = "ProtoTypeB"

        def received_message(self, src, msg):
            self.calls.append((src, msg))

    tl = Timeline()
    qn = DQCNode("qn", tl, data_memo_size=1, memo_size=1)

    pA = ProtoTypeA()
    pB = ProtoTypeB()
    qn.protocols.extend([pA, pB])

    # Should go only to protocols where type(p) == msg.protocol_type
    qn.receive_message("peer", SimpleMsg(protocol_type="ProtoTypeA"))

    assert len(pA.calls) == 1 and pA.calls[0][0] == "peer"
    assert len(pB.calls) == 0

