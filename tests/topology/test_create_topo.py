"""Tests for CreateTopo — programmatic topology construction without a config file."""

from sequence.topology.create_topo import CreateTopo
from sequence.topology.network_impls import BsmNetworkImpl
from sequence.topology.const_topo import QUANTUM_ROUTER, BSM_NODE


def _simple_topo():
    return CreateTopo(
        impl         = BsmNetworkImpl(),
        nodes        = [
            {"name": "r1", "type": "QuantumRouter", "seed": 0, "memo_size": 10},
            {"name": "r2", "type": "QuantumRouter", "seed": 1, "memo_size": 10},
        ],
        qconnections = [
            {"node1": "r1", "node2": "r2", "attenuation": 0.0002,
             "distance": 2000, "type": "meet_in_the_middle"},
        ],
        cconnections = [
            {"node1": "r1", "node2": "r2", "delay": 1_000_000_000},
        ],
        stop_time = 1e12,
    )


def test_nodes_created():
    topo = _simple_topo()
    nodes = topo.get_nodes()
    assert QUANTUM_ROUTER in nodes
    assert BSM_NODE in nodes
    assert len(nodes[QUANTUM_ROUTER]) == 2
    assert len(nodes[BSM_NODE]) == 1


def test_bsm_auto_named():
    topo = _simple_topo()
    bsm = topo.get_nodes()[BSM_NODE][0]
    assert bsm.name == "BSM.r1.r2.auto"


def test_channels():
    topo = _simple_topo()
    assert len(topo.get_qchannels()) == 2
    assert len(topo.get_cchannels()) == 6  # 4 from BSM auto-create + 2 from bidirectional cconnection


def test_timeline():
    topo = _simple_topo()
    assert topo.get_timeline().stop_time == 1e12
