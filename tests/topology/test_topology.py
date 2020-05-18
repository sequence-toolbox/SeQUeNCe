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
    config_file = "tests/topology/topology.json"
    topo.load_config(config_file)
    config = json5.load(open(config_file))

    # check if have all nodes plus extra middle node
    assert len(topo.nodes) == len(config["nodes"]) + 1
    assert topo.graph["alice"] == {"bob": 3e3}


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
    channels = [e for e in tl.entities if type(e) == ClassicalChannel]
    assert len(channels) == 1
    assert channels[0].ends == [n1, n2]


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

    topo.add_quantum_connection("n3", "n4", attenuation=1e-5, distance=1e3)

    assert len(topo.nodes) == 5 # added middle node
    assert topo.graph["n3"] == {"middle_n3_n4": 500}
    channels = [e for e in tl.entities if type(e) == QuantumChannel]
    assert len(channels) == 3


def test_get_nodes_by_type():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    n1 = Node("n1", tl)
    n2 = QuantumRouter("n2", tl)
    n3 = MiddleNode("n3", tl, ["n2","n4"])
    n4 = QuantumRouter("n4", tl)
    topo.add_node(n1)
    topo.add_node(n2)
    topo.add_node(n3)
    topo.add_node(n4)

    nodes = topo.get_nodes_by_type("QuantumRouter")
    print(topo.nodes.items())

    assert nodes == [n2, n4]


