from sequence.topology.dqc_net_topo import DQCNetTopo
from sequence.kernel.timeline import Timeline


def test_sequential_simulation_quantum_node_topo_simple():
    topo = DQCNetTopo("tests/topology/quantum_node_net_topo_simple.json")

    # timeline
    assert isinstance(topo.get_timeline(), Timeline)
    assert topo.get_timeline().stop_time == 100

    # nodes dict has QuantumNode and BSMNode
    nodes = topo.get_nodes()
    assert DQCNetTopo.DQC_NODE in nodes
    assert DQCNetTopo.BSM_NODE in nodes
    assert len(nodes[DQCNetTopo.DQC_NODE]) == 2
    assert len(nodes[DQCNetTopo.BSM_NODE]) == 1

    q1, q2 = sorted(nodes[DQCNetTopo.DQC_NODE], key=lambda n: n.name)
    # channels: 2 QCs (q1->BSM, q2->BSM), 6 CCs (4 via BSM, 2 direct)
    assert len(topo.get_qchannels()) == 2
    assert len(topo.get_cchannels()) == 6

    # check QC params and capture the auto BSM name
    qc_list = topo.get_qchannels()
    for qc in qc_list:
        assert qc.distance == 500    # 1000 // 2
        assert qc.attenuation == 0.0002
    bsm_name = qc_list[0].receiver
    assert bsm_name.startswith("BSM.")

    # verify classical delays: 0.5e9 when to/from BSM, else 1e9 for direct q1<->q2
    for cc in topo.get_cchannels():
        if cc.sender.name == bsm_name or cc.receiver == bsm_name:
            assert cc.delay == 500_000_000
        else:
            # should be q1->q2 or q2->q1
            assert {cc.sender.name, cc.receiver} == {"q1", "q2"}
            assert cc.delay == 1_000_000_000

    # each node should have a data memory array (name include "Data")
    for qn in (q1, q2):
        memory_array = qn.get_components_by_type("MemoryArray")
        assert any("Data" in getattr(ma, "name", "") for ma in memory_array)

    # wiring presence checks
    assert bsm_name in q1.qchannels and bsm_name in q2.qchannels
    assert bsm_name in q1.cchannels and bsm_name in q2.cchannels
    assert "q2" in q1.cchannels and "q1" in q2.cchannels

    # forwarding table should route q1 <-> q2
    for qn in (q1, q2):
        routing = qn.network_manager.protocol_stack[0]  # routing protocol at bottom of stack
        assert len(routing.forwarding_table) >= 1
        # ensure it knows how to reach the other node
        other = "q2" if qn.name == "q1" else "q1"
        assert other in routing.forwarding_table
