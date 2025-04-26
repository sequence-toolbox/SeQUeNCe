from sequence.topology.qlan_star_topo import QlanStarTopo
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