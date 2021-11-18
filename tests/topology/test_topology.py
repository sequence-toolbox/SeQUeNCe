import json5

from sequence.topology.topology import Topology
from sequence.kernel.timeline import Timeline
from sequence.topology.node import *
from sequence.components.optical_channel import *


def test_load_config():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    # NOTE: test should be run from Sequence-python directory
    #   if test needs to be run from a different directory, rewrite path
    #   this also applies to the next test (test_load_config_2)
    config_file = "tests/topology/topology.json"
    topo.load_config(config_file)
    config = json5.load(open(config_file))

    # check if have all nodes plus extra middle node
    assert len(topo.nodes) == len(config["nodes"]) + 1
    assert topo.graph["alice"] == {"bob": 3e3}


def test_load_config_2():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    config_file = "example/starlight.json"
    topo.load_config(config_file)
    config = json5.load(open(config_file))

    assert len(topo.nodes) == len(config["nodes"]) + 10
    assert len(topo.cchannels) == (36 * 2) + (10 * 4)  # number of all-to-all connections plus middle node connectivity
    starlight = topo.nodes["StarLight"]
    assert starlight.cchannels["NU"].delay == 0.79e9 / 2  # round trip / 2

    # test generated forwarding table
    table = starlight.network_manager.protocol_stack[0].forwarding_table
    print(table)
    assert table["NU"] == "NU"
    assert table["UChicago_HC"] == "UChicago_PME"
    assert table["Argonne_2"] == "Argonne_1"


def test_add_node():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    n1 = Node("n1", tl)
    topo.add_node(n1)
    assert len(topo.nodes) == 1
    assert topo.nodes["n1"] == n1


def test_add_classical_connection():
    tl = Timeline()
    topo = Topology("test_topo", tl)
    
    n1 = Node("n1", tl)
    n2 = Node("n2", tl)
    topo.add_node(n1)
    topo.add_node(n2)

    topo.add_classical_connection("n1", "n2", distance=1e3)
    
    assert topo.graph["n1"] == {}
    channels: List[ClassicalChannel] = [e for e in tl.entities.values() if
                                        type(e) == ClassicalChannel]
    assert len(channels) == 2
    for channel in channels:
        if channel.sender == n1:
            assert channel.receiver == n2.name
        elif channel.sender == n2:
            assert channel.receiver == n1.name
        else:
            assert False


def test_add_quantum_connection():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    n1 = Node("n1", tl)
    n2 = Node("n2", tl)
    n3 = QuantumRouter("n3", tl)
    n4 = QuantumRouter("n4", tl)
    topo.add_node(n1)
    topo.add_node(n2)
    topo.add_node(n3)
    topo.add_node(n4)

    topo.add_quantum_connection("n1", "n2", attenuation=1e-5, distance=1e3)

    assert topo.graph["n1"] == {"n2": 1e3}
    assert topo.graph["n2"] == {"n1": 1e3}

    topo.add_quantum_connection("n3", "n4", attenuation=1e-5, distance=1e3)

    assert len(topo.nodes) == 5 # added middle node
    assert topo.graph["n3"] == {"middle_n3_n4": 500}
    channels = [e for e in tl.entities.values() if type(e) == QuantumChannel]
    assert len(channels) == 4 # 2 for each connection


def test_get_nodes_by_type():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    n1 = Node("n1", tl)
    n2 = QuantumRouter("n2", tl)
    n3 = BSMNode("n3", tl, ["n2","n4"])
    n4 = QuantumRouter("n4", tl)
    topo.add_node(n1)
    topo.add_node(n2)
    topo.add_node(n3)
    topo.add_node(n4)

    nodes = topo.get_nodes_by_type("QuantumRouter")
    print(topo.nodes.items())

    assert nodes == [n2, n4]


