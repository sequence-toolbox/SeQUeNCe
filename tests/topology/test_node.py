from sequence.components.optical_channel import *
from sequence.components.optical_channel import QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.protocol import Protocol
from sequence.topology.node import Node, QuantumRouter, MiddleNode


class FakeProtocol(Protocol):
    def __init__(self):
        self.flag = False

    def init(self):
        self.flag = True

    def pop(self):
        pass

    def push(self):
        pass

    def received_message(self, src, msg):
        pass


def test_Node_init():
    tl = Timeline()
    node = Node("node", tl)
    node.protocols.append(FakeProtocol())
    assert node.protocols[0].flag is False
    tl.init()
    assert node.protocols[0].flag is True


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
    cc = ClassicalChannel("cc", tl, 1e3)
    cc.set_ends(node1, node2)
    for i in range(10):
        node1.send_message("node2", str(i))
        tl.time += 1

    for i in range(10):
        node2.send_message("node1", str(i))
        tl.time += 1

    assert len(node1.log) == len(node2.log) == 0
    tl.init()
    tl.run()

    expect_res = [(5000010, 'node2', '0'), (5000011, 'node2', '1'), (5000012, 'node2', '2'), (5000013, 'node2', '3'),
                  (5000014, 'node2', '4'), (5000015, 'node2', '5'), (5000016, 'node2', '6'), (5000017, 'node2', '7'),
                  (5000018, 'node2', '8'), (5000019, 'node2', '9')]

    for actual, expect in zip(node1.log, expect_res):
        assert actual == expect

    expect_res = [(5000000, 'node1', '0'), (5000001, 'node1', '1'), (5000002, 'node1', '2'), (5000003, 'node1', '3'),
                  (5000004, 'node1', '4'), (5000005, 'node1', '5'), (5000006, 'node1', '6'), (5000007, 'node1', '7'),
                  (5000008, 'node1', '8'), (5000009, 'node1', '9')]

    for actual, expect in zip(node2.log, expect_res):
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
    qc = QuantumChannel("qc", tl, 2e-4, 2e4)
    qc.set_ends(node1, node2)
    tl.init()

    for i in range(10):
        photon = Photon(str(i))
        node1.send_qubit("node2", photon)
        tl.time += 1

    for i in range(10):
        photon = Photon(str(i))
        node2.send_qubit("node1", photon)
        tl.time += 1

    assert len(node1.log) == len(node2.log) == 0
    tl.run()

    expect_res = [(100000010, 'node2', '0'), (100000013, 'node2', '3'), (100000017, 'node2', '7'),
                  (100000018, 'node2', '8'), (100000019, 'node2', '9')]

    for ans, expect in zip(node1.log, expect_res):
        assert ans == expect

    expect_res = [(100000001, 'node1', '1'), (100000002, 'node1', '2'), (100000005, 'node1', '5'),
                  (100000007, 'node1', '7'), (100000008, 'node1', '8')]

    for ans, expect in zip(node2.log, expect_res):
        assert ans == expect


def test_QuantumRouter_init():
    tl = Timeline()
    node1 = QuantumRouter("node1", tl)
    for i in range(2, 50):
        node = QuantumRouter("node%d" % i, tl)
        mid = MiddleNode("mid%d" % i, tl, [node1.name, node.name])
        qc = QuantumChannel("qc_l_%d" % i, tl, 0, 1000)
        qc.set_ends(node1, mid)
        qc = QuantumChannel("qc_r_%d" % i, tl, 0, 1000)
        qc.set_ends(node, mid)

    node1.init()

    assert len(node1.map_to_middle_node) == 48
    for i in range(2, 50):
        node_name = "node%d" % i
        assert node1.map_to_middle_node[node_name] == "mid%d" % i
