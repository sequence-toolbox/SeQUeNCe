from sequence.topology.qkd_topo import QKDTopo
from sequence.topology.node import QKDNode
from sequence.kernel.timeline import Timeline


def test_QKDTopology():
    topo = QKDTopo("tests/topology/qkd_net_topo_sample_config.json")
    assert isinstance(topo.get_timeline(), Timeline)
    assert topo.get_timeline().stop_time == 1000000000000

    all_nodes = topo.get_nodes()
    assert len(all_nodes) == 1 and QKDTopo.QKD_NODE in all_nodes
    qkd_nodes = topo.get_nodes_by_type(QKDTopo.QKD_NODE)
    assert len(qkd_nodes) == 2

    for node in qkd_nodes:
        assert isinstance(node, QKDNode)
        assert len(node.cchannels) == 1
        if node.name == "alice":
            assert len(node.qchannels) == 1
        else:
            assert len(node.qchannels) == 0

    for cc in topo.get_cchannels():
        assert cc.delay == 1000000000

    for qc in topo.get_qchannels():
        assert qc.distance == 3e3
        assert qc.attenuation == 1e-5
