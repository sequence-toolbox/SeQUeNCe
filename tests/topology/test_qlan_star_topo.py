import pytest

from sequence.topology.qlan_star_topo import QlanStarTopo
from sequence.topology.const_topo import ORCHESTRATOR, CLIENT
from sequence.topology.qlan.orchestrator import QlanOrchestratorNode
from sequence.kernel.timeline import Timeline

TOPOLOGY = "tests/topology/qlan_topo_sample_config.json"

def test_timeline_initialization():
    qlan_topo = QlanStarTopo(TOPOLOGY)
    assert isinstance(qlan_topo.get_timeline(), Timeline)
    assert qlan_topo.get_timeline().stop_time == 1000000000000


def test_nodes_initialization():
    qlan_topo = QlanStarTopo(TOPOLOGY)
    all_nodes = qlan_topo.get_nodes()

    assert len(qlan_topo.meas_bases) == qlan_topo.n_local_memories
    assert qlan_topo.meas_bases == 'z'

    assert len(qlan_topo.orchestrator_nodes)+len(qlan_topo.client_nodes) == 3
    assert QlanStarTopo.ORCHESTRATOR in all_nodes
    assert QlanStarTopo.CLIENT in all_nodes

    orch_nodes = qlan_topo.get_nodes_by_type(QlanStarTopo.ORCHESTRATOR)
    assert len(orch_nodes) == 1

    for node in orch_nodes:
        assert isinstance(node, QlanOrchestratorNode)
        assert len(node.cchannels) == 2


def test_cchannels_initialization():
    qlan_topo = QlanStarTopo(TOPOLOGY)
    for cc in qlan_topo.get_cchannels():
        assert cc.delay == 500000000


def test_qchannels_initialization():
    qlan_topo = QlanStarTopo(TOPOLOGY)
    for qc in qlan_topo.get_qchannels():
        assert qc.distance == 3000
        assert qc.attenuation == 1e-5



_MEM = dict(
    memo_fidelity_orch=0.9,   memo_frequency_orch=2000,
    memo_efficiency_orch=1,   memo_coherence_orch=-1,   memo_wavelength_orch=500,
    memo_fidelity_client=0.9, memo_frequency_client=2000,
    memo_efficiency_client=1, memo_coherence_client=-1, memo_wavelength_client=500,
)

_ORCH = {"name": "orch", "type": "QlanOrchestratorNode", "seed": 0}
_C1 = {"name": "c1", "type": "QlanClientNode", "seed": 1}
_C2 = {"name": "c2", "type": "QlanClientNode", "seed": 2}


def _make_ordering_topo(nodes, local_memories=1, measurement_bases="z", client_number=2):
    return QlanStarTopo(
        {"nodes": nodes, "stop_time": 1e12},
        local_memories=local_memories,
        client_number=client_number,
        measurement_bases=measurement_bases,
        **_MEM,
    )


def test_ordering_orch_listed_first():
    topo = _make_ordering_topo([_ORCH, _C1, _C2])
    assert len(topo.get_nodes_by_type(ORCHESTRATOR)) == 1
    assert len(topo.get_nodes_by_type(CLIENT)) == 2


def test_ordering_clients_listed_first():
    topo = _make_ordering_topo([_C1, _C2, _ORCH])
    assert len(topo.get_nodes_by_type(ORCHESTRATOR)) == 1
    assert len(topo.get_nodes_by_type(CLIENT)) == 2


def test_zero_clients_raises():
    with pytest.raises(ValueError):
        _make_ordering_topo([_ORCH], client_number=0)


def test_client_count_exceeds_node_list_raises():
    with pytest.raises(ValueError):
        _make_ordering_topo(
            [_ORCH, _C1, _C2],
            local_memories=2,
            measurement_bases="zz",
            client_number=2,
        )
