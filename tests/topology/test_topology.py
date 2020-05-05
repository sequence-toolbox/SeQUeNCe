import json5

from sequence.topology.topology import Topology
from sequence.kernel.timeline import Timeline
from sequence.topology.node import *


def test_load_config():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    # NOTE: test should be run from Sequence-python directory
    #   if test needs to be run from a different directory, rewrite path
    config_file = "tests/topology/topology.json"
    topo.load_config(config_file)
    config = json5.load(open(config_file)) 


def test_add_node():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    n1 = Node("n1", tl)
    topo.add_node(n1)
    assert len(topo.nodes) == 1
    assert topo.nodes["n1"] == n1


def test_add_connection_individual():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    n1 = Node("n1", tl)
    n2 = Node("n2", tl)
    topo.add_node(n1)
    topo.add_node(n2)

    # contains info for quantum and classical
    connection_params = {"distance": 1e3, "attenuation": 1e-5, "delay": 1e9}

    topo.add_quantum_connection("n1", "n2", **connection_params)
    topo.add_classical_connection("n1", "n2", **connection_params)

    assert topo.qchannels[0].distance == 1e3
    assert topo.qchannels[0].ends == [n1, n2]
    assert topo.cchannels[0].delay == 1e9


