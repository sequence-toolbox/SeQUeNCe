"""CreateTopo — programmatic topology construction without a config file.

Passes Python dicts directly instead of a JSON config.
Standard BsmNetworkImpl handles the rest.
"""

from sequence.topology.create_topo import CreateTopo
from sequence.topology.network_impls import BsmNetworkImpl
from sequence.topology.const_topo import QUANTUM_ROUTER, BSM_NODE


impl = BsmNetworkImpl()

topo = CreateTopo(
    impl      = impl,
    stop_time = 10e12,
    nodes = [
        {"name": "a", "type": "QuantumRouter", "seed": 0, "memo_size": 5},
        {"name": "b", "type": "QuantumRouter", "seed": 1, "memo_size": 5},
    ],
    qconnections = [
        {"node1": "a", "node2": "b", "attenuation": 0, "distance": 1000,
         "type": "meet_in_the_middle", "seed": 2},
    ],
    cconnections = [
        {"node1": "a", "node2": "b", "delay": int(1e9)},
    ],
)

print("Routers:", [n.name for n in topo.get_nodes_by_type(QUANTUM_ROUTER)])
print("BSM nodes:", [n.name for n in topo.get_nodes_by_type(BSM_NODE)])
print("Quantum channels:", [qc.name for qc in topo.get_qchannels()])
print("Classical channels:", [cc.name for cc in topo.get_cchannels()])
