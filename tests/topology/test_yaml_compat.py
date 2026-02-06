"""Tests that all topology classes load YAML configs identically to JSON."""

from sequence.topology.qkd_topo import QKDTopo
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.qlan_star_topo import QlanStarTopo
from sequence.topology.dqc_net_topo import DQCNetTopo
from sequence.kernel.timeline import Timeline
from sequence.constants import (
    QKD_NODE, QUANTUM_ROUTER, BSM_NODE,
    ORCHESTRATOR, CLIENT, DQC_NODE,
)

JSON_DIR = "tests/topology"
YAML_DIR = "tests/topology"


# --- QKDTopo ---

def test_qkd_yaml_matches_json():
    json_topo = QKDTopo(f"{JSON_DIR}/qkd_net_topo_sample_config.json")
    yaml_topo = QKDTopo(f"{YAML_DIR}/qkd_net_topo_sample_config.yaml")

    assert yaml_topo.get_timeline().stop_time == json_topo.get_timeline().stop_time

    json_nodes = json_topo.get_nodes()
    yaml_nodes = yaml_topo.get_nodes()
    assert json_nodes.keys() == yaml_nodes.keys()
    assert len(yaml_topo.get_nodes_by_type(QKD_NODE)) == len(
        json_topo.get_nodes_by_type(QKD_NODE)
    )

    json_qcs = json_topo.get_qchannels()
    yaml_qcs = yaml_topo.get_qchannels()
    assert len(yaml_qcs) == len(json_qcs)
    for jqc, yqc in zip(json_qcs, yaml_qcs):
        assert yqc.distance == jqc.distance
        assert yqc.attenuation == jqc.attenuation

    json_ccs = json_topo.get_cchannels()
    yaml_ccs = yaml_topo.get_cchannels()
    assert len(yaml_ccs) == len(json_ccs)
    for jcc, ycc in zip(json_ccs, yaml_ccs):
        assert ycc.delay == jcc.delay


# --- RouterNetTopo ---

def test_router_yaml_matches_json():
    json_topo = RouterNetTopo(f"{JSON_DIR}/router_net_topo_sample_config.json")
    yaml_topo = RouterNetTopo(f"{YAML_DIR}/router_net_topo_sample_config.yaml")

    assert yaml_topo.get_timeline().stop_time == json_topo.get_timeline().stop_time

    json_nodes = json_topo.get_nodes()
    yaml_nodes = yaml_topo.get_nodes()
    assert json_nodes.keys() == yaml_nodes.keys()
    assert len(yaml_nodes[QUANTUM_ROUTER]) == len(json_nodes[QUANTUM_ROUTER])
    assert len(yaml_nodes[BSM_NODE]) == len(json_nodes[BSM_NODE])

    assert len(yaml_topo.get_qchannels()) == len(json_topo.get_qchannels())
    assert len(yaml_topo.get_cchannels()) == len(json_topo.get_cchannels())

    # verify memory fidelities match (template-based e1 vs default others)
    for jnode, ynode in zip(
        sorted(json_nodes[QUANTUM_ROUTER], key=lambda n: n.name),
        sorted(yaml_nodes[QUANTUM_ROUTER], key=lambda n: n.name),
    ):
        j_memos = jnode.get_components_by_type("MemoryArray")[0]
        y_memos = ynode.get_components_by_type("MemoryArray")[0]
        assert len(y_memos) == len(j_memos)
        for jm, ym in zip(j_memos, y_memos):
            assert ym.raw_fidelity == jm.raw_fidelity

    # forwarding tables populated
    for r in yaml_topo.get_nodes_by_type(QUANTUM_ROUTER):
        assert len(r.network_manager.protocol_stack[0].forwarding_table) > 0


# --- QlanStarTopo ---

def test_qlan_yaml_matches_json():
    json_topo = QlanStarTopo(f"{JSON_DIR}/qlan_topo_sample_config.json")
    yaml_topo = QlanStarTopo(f"{YAML_DIR}/qlan_topo_sample_config.yaml")

    assert yaml_topo.get_timeline().stop_time == json_topo.get_timeline().stop_time

    json_nodes = json_topo.get_nodes()
    yaml_nodes = yaml_topo.get_nodes()
    assert json_nodes.keys() == yaml_nodes.keys()
    assert len(yaml_topo.get_nodes_by_type(ORCHESTRATOR)) == len(
        json_topo.get_nodes_by_type(ORCHESTRATOR)
    )
    assert len(yaml_topo.get_nodes_by_type(CLIENT)) == len(
        json_topo.get_nodes_by_type(CLIENT)
    )

    assert len(yaml_topo.get_qchannels()) == len(json_topo.get_qchannels())
    assert len(yaml_topo.get_cchannels()) == len(json_topo.get_cchannels())

    for jcc, ycc in zip(json_topo.get_cchannels(), yaml_topo.get_cchannels()):
        assert ycc.delay == jcc.delay


# --- DQCNetTopo ---

def test_dqc_yaml_matches_json():
    json_topo = DQCNetTopo(f"{JSON_DIR}/dqc_node_net_topo_simple.json")
    yaml_topo = DQCNetTopo(f"{YAML_DIR}/dqc_node_net_topo_simple.yaml")

    assert yaml_topo.get_timeline().stop_time == json_topo.get_timeline().stop_time

    json_nodes = json_topo.get_nodes()
    yaml_nodes = yaml_topo.get_nodes()
    assert json_nodes.keys() == yaml_nodes.keys()
    assert len(yaml_nodes[DQC_NODE]) == len(json_nodes[DQC_NODE])
    assert len(yaml_nodes[BSM_NODE]) == len(json_nodes[BSM_NODE])

    assert len(yaml_topo.get_qchannels()) == len(json_topo.get_qchannels())
    assert len(yaml_topo.get_cchannels()) == len(json_topo.get_cchannels())

    # verify QC params match
    for jqc, yqc in zip(json_topo.get_qchannels(), yaml_topo.get_qchannels()):
        assert yqc.distance == jqc.distance
        assert yqc.attenuation == jqc.attenuation

    # forwarding tables populated
    for qn in yaml_topo.get_nodes_by_type(DQC_NODE):
        routing = qn.network_manager.get_routing_protocol()
        assert len(routing.forwarding_table) >= 1
