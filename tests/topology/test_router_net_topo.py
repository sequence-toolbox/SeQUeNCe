from sequence.topology.router_net_topo import RouterNetTopo
from sequence.kernel.timeline import Timeline


def test_sequential_simulation():
    topo = RouterNetTopo("tests/topology/router_net_topo_sample_config.json")
    assert isinstance(topo.get_timeline(), Timeline)
    assert topo.get_timeline().stop_time == 100
    all_nodes = topo.get_nodes()
    assert len(all_nodes) == 2
    assert RouterNetTopo.QUANTUM_ROUTER in all_nodes
    assert RouterNetTopo.BSM_NODE in all_nodes
    assert len(all_nodes[RouterNetTopo.QUANTUM_ROUTER]) == 4
    assert len(all_nodes[RouterNetTopo.BSM_NODE]) == 2
    assert len(topo.get_qchannels()) == 4
    assert len(topo.get_cchannels()) == 10

    routers = all_nodes[RouterNetTopo.QUANTUM_ROUTER]
    e1 = e2 = e3 = e4 = None
    for router in routers:
        memory_array = router.get_components_by_type("MemoryArray")[0]
        assert len(memory_array) == 20
        assert len(router.qchannels) == 1
        assert len(router.cchannels) == 2
        if router.name == "e1":
            e1 = router
        elif router.name == "e2":
            e2 = router
        elif router.name == "e3":
            e3 = router
        elif router.name == "e4":
            e4 = router
        else:
            raise ValueError("the topology file contains unknown node")

    for qc in topo.get_qchannels():
        assert qc.distance == 1000
        assert qc.attenuation == 0.0002

    assert "e2" in e1.cchannels and "bsm0" in e1.cchannels
    assert "e1" in e2.cchannels and "bsm0" in e2.cchannels
    assert "bsm0" in e1.qchannels and "bsm0" in e2.qchannels
    assert "e3" in e4.cchannels and "e4" in e3.cchannels
    e3_qc = list(e3.qchannels.values())[0]
    e4_qc = list(e4.qchannels.values())[0]
    assert e3_qc.receiver == e4_qc.receiver

    generated_bsm_name = e3_qc.receiver
    assert e1.map_to_middle_node["e2"] == e2.map_to_middle_node["e1"] == "bsm0"
    assert e3.map_to_middle_node["e4"] == e4.map_to_middle_node["e3"] \
           == generated_bsm_name

    for cc in topo.get_cchannels():
        if cc.sender.name == generated_bsm_name \
                or cc.receiver == generated_bsm_name:
            assert cc.delay == 500000000
        else:
            assert cc.delay == 1000000000

    for r in topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        assert len(r.network_manager.protocol_stack[0].forwarding_table) > 0

# TODO: unit test for the parallel simulation
