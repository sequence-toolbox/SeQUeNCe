import json5

from sequence.topology.topology import Topology
from sequence.kernel.timeline import Timeline


def test_load_config():
    tl = Timeline()
    topo = Topology("test_topo", tl)

    topo.load_config("tests/topology/topology.json")

    for name in topo.nodes:
        print(name)
    assert False


