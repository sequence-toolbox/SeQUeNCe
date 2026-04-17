from sequence.constants import SECOND
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.utils import nx_converter, graphs
import pytest

GRAPHS = {
    'linear': graphs.build_linear(25),
    'ring': graphs.build_ring(25),
    'star': graphs.build_star(25),
    'two_nodes': graphs.build_linear(2),
}

@pytest.fixture(params=GRAPHS.keys())
def graph(request):
    return GRAPHS[request.param]

@pytest.fixture
def config_and_map(graph):
    config, graph_map = nx_converter.generate_config(graph, 2000, 0.0002, 1)
    return config, graph_map, graph

@pytest.fixture
def topo_map(config_and_map):
    config, name_map, graph = config_and_map
    topo = RouterNetTopo(config)
    return topo, name_map, graph

class TestGenerateConfig:
    def test_router_count(self, config_and_map):
        config, _, graph = config_and_map
        routers = [n for n in config['nodes'] if n['type'] == 'QuantumRouter']
        assert len(routers) == graph.number_of_nodes()
    
    def test_bsm_count(self, config_and_map):
        """There should be a BSM per edge to facilitate MIM"""
        config, _, graph = config_and_map
        bsms = [n for n in config['nodes'] if n['type'] == 'BSMNode']
        assert len(bsms) == graph.number_of_edges()

    def test_qchannel_count(self, config_and_map):
        config, _, graph = config_and_map
        assert len(config['qchannels']) == 2 * graph.number_of_edges()
    
    def test_cchannel_count(self, config_and_map):
        config, _, graph = config_and_map
        n = graph.number_of_nodes()
        assert len(config['cchannels']) == n*(n-1) + 4 * graph.number_of_edges()

    def test_map_complete(self, config_and_map):
        config, graph_map, graph = config_and_map
        assert set(graph_map.keys()) == set(graph.nodes)
        assert len(set(graph_map.values())) == graph.number_of_nodes()

    def test_stop_time(self):
        config, *_ = nx_converter.generate_config(graphs.build_linear(2), 2000, 0.0002, 1, stop_time=100)
        assert config['stop_time'] == int(100 * SECOND)
    
    def test_absent_stop(self):
        config, *_ = nx_converter.generate_config(graphs.build_linear(2), 2000, 0.0002, 1)
        assert 'stop_time' not in config

    def test_default_template(self):
        config, *_ = nx_converter.generate_config(graphs.build_linear(2), 2000, 0.0002, 1)
        assert 'router_template' in config['templates']
        assert 'bsm_template' in config['templates']
    
    def test_template_references(self):
        config, *_ = nx_converter.generate_config(graphs.build_linear(2), 2000, 0.0002, 1)
        assert all(n['template'] == ('router_template' if n['type'] == 'QuantumRouter' else 'bsm_template') for n in config['nodes'])


class TestRouterNetTopo:
    def test_config_loads(self, topo_map):
        topo, _, graph = topo_map
        assert topo.get_timeline() is not None
        nodes = topo.get_nodes()
        assert len(nodes[RouterNetTopo.QUANTUM_ROUTER]) == graph.number_of_nodes()
        assert len(nodes[RouterNetTopo.BSM_NODE]) == graph.number_of_edges()