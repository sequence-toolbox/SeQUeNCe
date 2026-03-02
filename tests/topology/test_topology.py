from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.dqc_net_topo import DQCNetTopo
from sequence.topology.qkd_topo import QKDTopo
from sequence.topology.qlan_star_topo import QlanStarTopo
from sequence.topology.const_topo import QUANTUM_ROUTER


_TOPO_CONFIGS = {
    "router": ("tests/topology/router_net_topo_sample_config", RouterNetTopo),
    "dqc":    ("tests/topology/dqc_node_net_topo_simple",      DQCNetTopo),
    "qkd":    ("tests/topology/qkd_net_topo_sample_config",    QKDTopo),
    "qlan":   ("tests/topology/qlan_topo_sample_config",       QlanStarTopo),
}


def test_yaml_matches_json_all_topos():
    for label, (base_path, topo_cls) in _TOPO_CONFIGS.items():
        json_topo = topo_cls(base_path + ".json")
        yaml_topo = topo_cls(base_path + ".yaml")

        assert yaml_topo.get_timeline().stop_time == json_topo.get_timeline().stop_time, \
            f"{label}: stop_time mismatch"

        json_nodes = json_topo.get_nodes()
        yaml_nodes = yaml_topo.get_nodes()
        assert json_nodes.keys() == yaml_nodes.keys(), \
            f"{label}: node category keys differ"

        for key in json_nodes:
            assert len(yaml_nodes[key]) == len(json_nodes[key]), \
                f"{label}: node count mismatch for '{key}'"

        assert len(yaml_topo.get_qchannels()) == len(json_topo.get_qchannels()), \
            f"{label}: qchannel count mismatch"
        assert len(yaml_topo.get_cchannels()) == len(json_topo.get_cchannels()), \
            f"{label}: cchannel count mismatch"


def test_kwargs_merge_into_file_config():
    for label, (base_path, topo_cls) in _TOPO_CONFIGS.items():
        topo = topo_cls(base_path + ".json", stop_time=1234)
        assert topo.get_timeline().stop_time == 1234, \
            f"{label}: stop_time override failed"


def test_kwargs_extend_config_file():
    topo = RouterNetTopo(
        "tests/topology/router_net_topo_sample_config.json",
        nodes=[{"name": "extra", "type": "QuantumRouter", "seed": 99, "memo_size": 5}],
    )
    routers = topo.get_nodes_by_type(QUANTUM_ROUTER)
    assert any(r.name == "extra" for r in routers)
