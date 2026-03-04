import pytest

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.const_topo import (
    ALL_NODE,
    BSM_NODE,
    CONNECT_NODE_1,
    CONNECT_NODE_2,
    MEET_IN_THE_MID,
    NAME,
    QUANTUM_ROUTER,
    ROLE_BSM_ENDPOINT,
    TYPE,
)
from sequence.kernel.timeline import Timeline
from sequence.topology.topology_families import BsmTopologyFamily
from sequence.topology.node import BSMNode, Node, QuantumRouter
from sequence.topology.topology import Topology


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

    # check if all nodes are correctly generated
    routers = all_nodes[RouterNetTopo.QUANTUM_ROUTER]
    e1 = e2 = e3 = e4 = None
    for router in routers:
        memory_array = router.get_components_by_type("MemoryArray")[0]
        assert len(memory_array) == 20
        assert len(router.qchannels) == 1
        assert len(router.cchannels) == 2
        if router.name == "e1":
            e1 = router
            for memo in memory_array:
                assert memo.raw_fidelity == 1.0  # this is determined by the template
        elif router.name == "e2":
            e2 = router
            for memo in memory_array:
                assert memo.raw_fidelity == 0.85  # this is the default value
        elif router.name == "e3":
            e3 = router
            for memo in memory_array:
                assert memo.raw_fidelity == 0.85
        elif router.name == "e4":
            e4 = router
            for memo in memory_array:
                assert memo.raw_fidelity == 0.85
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


def test_dict_config_builds_topology():
    topo = RouterNetTopo(
        {
            "nodes": [
                {"name": "r1", "type": "QuantumRouter", "seed": 0, "memo_size": 10},
                {"name": "r2", "type": "QuantumRouter", "seed": 1, "memo_size": 10},
            ],
            "qconnections": [{"node1": "r1", "node2": "r2", "attenuation": 0.0002,
                              "distance": 2000, "type": "meet_in_the_middle"}],
            "cconnections": [{"node1": "r1", "node2": "r2", "delay": 1_000_000_000}],
            "stop_time": 1e12,
        }
    )
    nodes = topo.get_nodes()
    assert QUANTUM_ROUTER in nodes and BSM_NODE in nodes
    assert len(nodes[QUANTUM_ROUTER]) == 2
    assert len(nodes[BSM_NODE]) == 1
    assert topo.get_nodes()[BSM_NODE][0].name == "BSM.r1.r2.auto"
    assert len(topo.get_qchannels()) == 2
    assert len(topo.get_cchannels()) == 6
    assert topo.get_timeline().stop_time == 1e12



@Node.register("NonBsmEndpointNode")
class NonBsmEndpointNode(Node):
    @classmethod
    def from_config(cls, name, tl, config, template, **kwargs):
        return cls(name, tl)

def test_reject_node_without_endpoint_role():
    config = {
        "nodes": [
            {"name": "n1", "type": "NonBsmEndpointNode", "seed": 0},
            {"name": "n2", "type": "QuantumRouter", "seed": 1, "memo_size": 4},
        ],
        "qconnections": [
            {
                "node1": "n1",
                "node2": "n2",
                "attenuation": 0.0002,
                "distance": 2000,
                "type": "meet_in_the_middle",
            }
        ],
        "cconnections": [
            {"node1": "n1", "node2": "n2", "delay": 1_000_000_000}
        ],
        "stop_time": 1e12,
    }

    with pytest.raises(TypeError, match=f"required topology role '{ROLE_BSM_ENDPOINT}'"):
        RouterNetTopo(config)



def test_accept_custom_midpoint_subclass():
    @Node.register("CustomMidpointNode")
    class CustomMidpointNode(BSMNode):
        @classmethod
        def from_config(cls, name, tl, config, template, **kwargs):
            return cls(name, tl, kwargs["others"], component_templates=template)

    topo = RouterNetTopo(
        {
            "nodes": [
                {"name": "r1", "type": "QuantumRouter", "seed": 0, "memo_size": 4},
                {"name": "r2", "type": "QuantumRouter", "seed": 1, "memo_size": 4},
                {"name": "m12", "type": "CustomMidpointNode", "seed": 2},
            ],
            "qchannels": [
                {"source": "r1", "destination": "m12", "attenuation": 0.0002, "distance": 500},
                {"source": "r2", "destination": "m12", "attenuation": 0.0002, "distance": 500},
            ],
            "cchannels": [
                {"source": "r1", "destination": "m12", "delay": 500_000_000},
                {"source": "m12", "destination": "r1", "delay": 500_000_000},
                {"source": "r2", "destination": "m12", "delay": 500_000_000},
                {"source": "m12", "destination": "r2", "delay": 500_000_000},
            ],
            "cconnections": [
                {"node1": "r1", "node2": "r2", "delay": 1_000_000_000},
            ],
            "stop_time": 1e12,
        }
    )

    assert len(topo.get_nodes_by_type("CustomMidpointNode")) == 1

def test_qconnection_expansion_choose_midpoint_from_endpoint_properties():
    @Node.register("Wavelength980Router")
    class Wavelength980Router(QuantumRouter):
        operating_wavelength = 980

        @classmethod
        def from_config(cls, name, tl, config, template, **kwargs):
            memo_size = config.get("memo_size", 0)
            return cls(name, tl, memo_size=memo_size, component_templates=template)

    @Node.register("Wavelength1550Router")
    class Wavelength1550Router(QuantumRouter):
        operating_wavelength = 1550

        @classmethod
        def from_config(cls, name, tl, config, template, **kwargs):
            memo_size = config.get("memo_size", 0)
            return cls(name, tl, memo_size=memo_size, component_templates=template)

    @Node.register("PropertyDrivenMidpoint")
    class PropertyDrivenMidpoint(BSMNode):
        @classmethod
        def from_config(cls, name, tl, config, template, **kwargs):
            return cls(name, tl, kwargs["others"], component_templates=template)

    class PropertyDrivenBsmFamily(BsmTopologyFamily):
        def _configure_family(self, config, templates):
            self._node_specs = {node[NAME]: node for node in config[ALL_NODE]}

        def _midpoint_type_for_qconnection(self, q_connect):
            node1 = q_connect[CONNECT_NODE_1]
            node2 = q_connect[CONNECT_NODE_2]
            node1_cls = Node._registry[self._node_specs[node1][TYPE]]
            node2_cls = Node._registry[self._node_specs[node2][TYPE]]
            if node1_cls.operating_wavelength != node2_cls.operating_wavelength:
                return "PropertyDrivenMidpoint"
            return "BSMNode"

    class PropertyDrivenTopo(Topology):
        def __init__(self, config):
            super().__init__(config, PropertyDrivenBsmFamily())

    topo = PropertyDrivenTopo(
        {
            "nodes": [
                {"name": "a", "type": "Wavelength980Router", "seed": 0, "memo_size": 4},
                {"name": "b", "type": "Wavelength1550Router", "seed": 1, "memo_size": 4},
                {"name": "c", "type": "Wavelength1550Router", "seed": 2, "memo_size": 4},
            ],
            "qconnections": [
                {
                    "node1": "a",
                    "node2": "b",
                    "attenuation": 0.0002,
                    "distance": 2000,
                    "type": MEET_IN_THE_MID,
                    "seed": 10,
                },
                {
                    "node1": "b",
                    "node2": "c",
                    "attenuation": 0.0002,
                    "distance": 2000,
                    "type": MEET_IN_THE_MID,
                    "seed": 11,
                },
            ],
            "cconnections": [
                {"node1": "a", "node2": "b", "delay": 1_000_000_000},
                {"node1": "b", "node2": "c", "delay": 1_000_000_000},
            ],
            "stop_time": 1e12,
        }
    )

    assert len(topo.get_nodes_by_type("PropertyDrivenMidpoint")) == 1
    assert len(topo.get_nodes_by_type("BSMNode")) == 1
