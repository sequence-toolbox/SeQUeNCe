from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node, QuantumRouter, BSMNode


def test_Node_assign_cchannel():
    tl = Timeline()
    node = Node("node1", tl)
    cc = ClassicalChannel("cc", tl, 1e3)
    node.assign_cchannel(cc, "node2")
    assert "node2" in node.cchannels and node.cchannels["node2"] == cc


def test_Node_assign_qchannel():
    tl = Timeline()
    node = Node("node1", tl)
    qc = QuantumChannel("qc", tl, 2e-4, 1e3)
    node.assign_qchannel(qc, "node2")
    assert "node2" in node.qchannels and node.qchannels["node2"] == qc


def test_Node_send_message():
    class FakeNode(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_message(self, src, msg):
            self.log.append((self.timeline.now(), src, msg))

    tl = Timeline()
    node1 = FakeNode("node1", tl)
    node2 = FakeNode("node2", tl)
    cc0 = ClassicalChannel("cc0", tl, 1e3)
    cc1 = ClassicalChannel("cc1", tl, 1e3)
    cc0.set_ends(node1, node2.name)
    cc1.set_ends(node2, node1.name)

    MSG_NUM = 10
    CC_DELAY = cc0.delay

    for i in range(MSG_NUM):
        node1.send_message("node2", str(i))
        tl.time += 1

    for i in range(MSG_NUM):
        node2.send_message("node1", str(i))
        tl.time += 1

    assert len(node1.log) == len(node2.log) == 0
    tl.init()
    tl.run()

    expect_node1_log = [(CC_DELAY + MSG_NUM + i, "node2", str(i))
                        for i in range(MSG_NUM)]
    for actual, expect in zip(node1.log, expect_node1_log):
        assert actual == expect

    expect_node2_log = [(CC_DELAY + i, "node1", str(i))
                        for i in range(MSG_NUM)]
    for actual, expect in zip(node2.log, expect_node2_log):
        assert actual == expect


def test_Node_send_qubit():
    from sequence.components.photon import Photon
    from numpy import random

    random.seed(0)

    class FakeNode(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_qubit(self, src, qubit):
            self.log.append((self.timeline.now(), src, qubit.name))

    tl = Timeline()
    node1 = FakeNode("node1", tl)
    node2 = FakeNode("node2", tl)
    qc0 = QuantumChannel("qc0", tl, 2e-4, 2e4)
    qc1 = QuantumChannel("qc1", tl, 2e-4, 2e4)
    qc0.set_ends(node1, node2.name)
    qc1.set_ends(node2, node1.name)
    tl.init()

    for i in range(1000):
        photon = Photon(str(i), tl)
        node1.send_qubit("node2", photon)
        tl.time += 1

    for i in range(1000):
        photon = Photon(str(i), tl)
        node2.send_qubit("node1", photon)
        tl.time += 1

    assert len(node1.log) == len(node2.log) == 0
    tl.run()

    expect_rate_0 = 1 - qc0.loss
    expect_rate_1 = 1 - qc1.loss
    assert abs(len(node1.log) / 1000 - expect_rate_1) < 0.1
    assert abs(len(node2.log) / 1000 - expect_rate_0) < 0.1
