"""Demo — building a network without a config file.

Same 4-router network as tests/topology/router_net_topo_sample_config.json,
but constructed entirely in Python. No JSON file on disk.

Run with:
    python -m example.architecture_demo.create_topo_demo
"""

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.const_topo import QUANTUM_ROUTER, BSM_NODE


def build_network():
    return RouterNetTopo(
        {
            "stop_time": 1e12,
        },
        nodes=[
            {"name": "e1", "type": "QuantumRouter", "seed": 0, "memo_size": 20,
             "template": "perfect_memo"},
            {"name": "e2", "type": "QuantumRouter", "seed": 1, "memo_size": 20},
            {"name": "e3", "type": "QuantumRouter", "seed": 2, "memo_size": 20},
            {"name": "e4", "type": "QuantumRouter", "seed": 3, "memo_size": 20},
            {"name": "bsm0", "type": "BSMNode",      "seed": 4},
        ],

        templates = {
            "perfect_memo": {
                "MemoryArray": {"fidelity": 1.0}
            }
        },

        # e1 <-> e2 are wired manually via explicit qchannels/cchannels above
        # e3 <-> e4 use qconnections so the BSM node is auto-created at the midpoint
        qchannels = [
            {"source": "e1", "destination": "bsm0", "attenuation": 0.0002, "distance": 1000},
            {"source": "e2", "destination": "bsm0", "attenuation": 0.0002, "distance": 1000},
        ],
        cchannels = [
            {"source": "e1", "destination": "bsm0", "delay": 1_000_000_000},
            {"source": "e2", "destination": "bsm0", "delay": 1_000_000_000},
            {"source": "e1", "destination": "e2",   "delay": 1_000_000_000},
            {"source": "e2", "destination": "e1",   "delay": 1_000_000_000},
        ],

        qconnections = [
            {"node1": "e3", "node2": "e4", "attenuation": 0.0002,
             "distance": 2000, "type": "meet_in_the_middle"},
        ],
        cconnections = [
            {"node1": "e3", "node2": "e4", "distance": 5000, "delay": 1_000_000_000},
        ],

    )


if __name__ == "__main__":
    topo = build_network()
    tl   = topo.get_timeline()

    routers = topo.get_nodes_by_type(QUANTUM_ROUTER)
    bsms    = topo.get_nodes_by_type(BSM_NODE)

    print(f"routers : {[r.name for r in routers]}")
    print(f"bsm nodes: {[b.name for b in bsms]}")
    print(f"qchannels: {len(topo.get_qchannels())}")
    print(f"cchannels: {len(topo.get_cchannels())}")

    e1 = tl.get_entity_by_name("e1")
    memo_array = e1.get_components_by_type("MemoryArray")[0]
    print(f"\ne1 memory fidelity (from template): {memo_array[0].raw_fidelity}")

    e2 = tl.get_entity_by_name("e2")
    memo_array = e2.get_components_by_type("MemoryArray")[0]
    print(f"e2 memory fidelity (default):       {memo_array[0].raw_fidelity}")

    tl.init()
    tl.run()
    print("\nsimulation ran ok")
