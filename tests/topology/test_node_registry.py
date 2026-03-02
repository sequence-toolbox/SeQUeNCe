import pytest
from sequence.topology.node import Node, BSMNode, QuantumRouter, DQCNode
from sequence.kernel.timeline import Timeline


def _tl():
    return Timeline(stop_time=1e12)


def test_builtins_registered():
    assert "BSMNode" in Node._registry
    assert "QuantumRouter" in Node._registry
    assert "DQCNode" in Node._registry


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown node type"):
        Node.create("NoSuchNode", "n", _tl(), {}, {})


def test_decorator_registration():
    @Node.register("TestNode")
    class TestNode(QuantumRouter):
        pass
    assert "TestNode" in Node._registry


def test_quantum_router_from_config():
    node = Node.create("QuantumRouter", "r1", _tl(), {"memo_size": 7}, {})
    assert isinstance(node, QuantumRouter)
    assert len(node.components[node.memo_arr_name]) == 7


def test_dqc_node_from_config():
    node = Node.create("DQCNode", "d1", _tl(), {"memo_size": 3, "data_memo_size": 2}, {})
    assert isinstance(node, DQCNode)
    assert len(node.components[node.data_memo_arr_name]) == 2


def test_bsm_node_from_config():
    node = Node.create("BSMNode", "bsm1", _tl(), {}, {}, others=["r1", "r2"])
    assert isinstance(node, BSMNode)
