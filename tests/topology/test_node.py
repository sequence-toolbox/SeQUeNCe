from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.timeline import Timeline
import pytest

from sequence.topology.node import Node, ClassicalNode, QuantumRouter, BSMNode, DQCNode
from sequence.topology.const_topo import ROLE_BSM_ENDPOINT


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

    expect_node1_log = [(CC_DELAY + MSG_NUM + i, "node2", str(i)) for i in range(MSG_NUM)]
    for actual, expect in zip(node1.log, expect_node1_log):
        assert actual == expect

    expect_node2_log = [(CC_DELAY + i, "node1", str(i)) for i in range(MSG_NUM)]
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


def test_ClassicalNode_send_message():
    class FakeNode(ClassicalNode):
        def __init__(self, name, tl):
            ClassicalNode.__init__(self, name, tl)
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

    expect_node1_log = [(CC_DELAY + MSG_NUM + i, "node2", str(i)) for i in range(MSG_NUM)]
    for actual, expect in zip(node1.log, expect_node1_log):
        assert actual == expect

    expect_node2_log = [(CC_DELAY + i, "node1", str(i)) for i in range(MSG_NUM)]
    for actual, expect in zip(node2.log, expect_node2_log):
        assert actual == expect


def test_builtins_registered():
    assert "BSMNode" in Node._registry
    assert "QuantumRouter" in Node._registry
    assert "DQCNode" in Node._registry


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown node type"):
        Node.create("NoSuchNode", "n", Timeline(stop_time=1e12), {}, {})


def test_decorator_registration():
    @Node.register("TestNode")
    class TestNode(QuantumRouter):
        pass

    assert "TestNode" in Node._registry


def test_registration_rejects_duplicate_type_names():
    @Node.register("DuplicateNameRouter")
    class DuplicateNameRouter(QuantumRouter):
        pass

    with pytest.raises(ValueError, match="already registered"):
        @Node.register("DuplicateNameRouter")
        class AnotherDuplicateNameRouter(QuantumRouter):
            pass


def test_quantum_router_from_config():
    node = Node.create("QuantumRouter", "r1", Timeline(stop_time=1e12), {"memo_size": 7}, {})
    assert isinstance(node, QuantumRouter)
    assert len(node.components[node.memo_arr_name]) == 7


def test_bsm_node_from_config():
    node = Node.create("BSMNode", "bsm1", Timeline(stop_time=1e12), {}, {}, others=["r1", "r2"])
    assert isinstance(node, BSMNode)


def test_dqc_node_from_config():
    node = Node.create("DQCNode", "d1", Timeline(stop_time=1e12), {"memo_size": 3, "data_memo_size": 2}, {})
    assert isinstance(node, DQCNode)
    assert len(node.components[node.data_memo_arr_name]) == 2


def test_subclass_inherits_endpoint_role():
    @Node.register("InheritedRoleRouter")
    class InheritedRoleRouter(QuantumRouter):
        @classmethod
        def from_config(cls, name, tl, config, template, **kwargs):
            memo_size = config.get("memo_size", 0)
            return cls(name, tl, memo_size=memo_size, component_templates=template)

    assert ROLE_BSM_ENDPOINT in InheritedRoleRouter.topology_roles
