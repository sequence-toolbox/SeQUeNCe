import subprocess
import sys

import pytest

from sequence.topology.dqc_net_topo import DQCNetTopo
from sequence.topology.qkd_topo import QKDTopo
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.utils.draw_topo import draw_topology, get_topology

ROUTER_CONFIG = "tests/topology/router_net_topo_sample_config.json"
QKD_CONFIG = "tests/topology/qkd_net_topo_sample_config.json"
DQC_CONFIG = "tests/topology/dqc_node_net_topo_simple.json"


def test_import_does_not_run_cli():
    """Importing the module must not parse arguments, read files, or draw."""
    result = subprocess.run([sys.executable, "-c", "import sequence.utils.draw_topo"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_get_topology_router_net():
    assert isinstance(get_topology(ROUTER_CONFIG), RouterNetTopo)


def test_get_topology_qkd():
    assert isinstance(get_topology(QKD_CONFIG), QKDTopo)


def test_get_topology_dqc_net():
    assert isinstance(get_topology(DQC_CONFIG), DQCNetTopo)


def test_get_topology_unknown_node_type(tmp_path):
    config_file = tmp_path / "unknown_net_topo.json"
    config_file.write_text('{"nodes": [{"name": "node_0", "type": "UnknownNode"}]}')

    with pytest.raises(Exception, match="Unknown node type 'UnknownNode'"):
        get_topology(str(config_file))


def test_draw_topology_without_middle():
    """The routers are joined directly, the BSM nodes between them are left out."""
    source = draw_topology(get_topology(ROUTER_CONFIG)).source

    for router in ("router_0", "router_1", "router_2"):
        assert router in source
    assert "BSM_router_0_router_1" not in source
    assert "BSM_router_1_router_2" not in source
    assert "router_0 -- router_1" in source
    assert "router_1 -- router_2" in source


def test_draw_topology_with_middle():
    """The BSM nodes are drawn, with one edge per quantum channel."""
    source = draw_topology(get_topology(ROUTER_CONFIG), draw_middle=True).source

    assert "BSM_router_0_router_1 [label=BSM shape=rectangle]" in source
    assert "BSM_router_1_router_2 [label=BSM shape=rectangle]" in source
    assert source.count(" -- ") == 4
    assert "router_0 -- BSM_router_0_router_1" in source
    assert "router_2 -- BSM_router_1_router_2" in source
