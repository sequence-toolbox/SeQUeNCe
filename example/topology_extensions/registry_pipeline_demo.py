"""Demo — registry pipeline with kwargs override and custom from_config.

This example displays the following capabilities:
1. Custom nodes slot into the build pipeline with zero core changes.
   The chain is: Topology._add_nodes reads "type" from your config →
   TopologyFamily._build_node calls Node.create(type, ...) →
   Node.create looks up the type in the registry and calls its
   from_config classmethod. So all you do is register + implement
   from_config, and the topology just builds your node like any builtin.
2. File-based configs can be overridden and extended at construction
   time via kwargs — scalars get replaced, lists get appended.

Run with:
    python example/topology_extensions/registry_pipeline_demo.py
"""

from pathlib import Path

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.node import Node, QuantumRouter
from sequence.topology.const_topo import BSM_NODE


@Node.register("InstrumentedRouter")
class InstrumentedRouter(QuantumRouter):
    """QuantumRouter that tracks entanglement generation attempts."""

    def __init__(self, name, tl, memo_size=50, seed=None,
                 component_templates=None, gate_fid=1, meas_fid=1):
        component_templates = component_templates or {}
        super().__init__(name, tl, memo_size, seed, component_templates, gate_fid, meas_fid)
        self.eg_attempt_count = 0

    def receive_qubit(self, src, qubit):
        self.eg_attempt_count += 1
        super().receive_qubit(src, qubit)

    @classmethod
    def from_config(cls, name, tl, config, template, **kwargs):
        memo_size = config.get("memo_size", 50)
        seed = config.get("seed", None)
        return cls(name, tl, memo_size, seed, component_templates=template)


if __name__ == "__main__":
    config_path = str(Path(__file__).with_name("registry_pipeline_demo.json"))

    # load from file, override stop_time, extend nodes list with a third router
    topo = RouterNetTopo(
        config_path,
        stop_time=5e12,
        nodes=[{"name": "r3", "type": "InstrumentedRouter", "seed": 2, "memo_size": 5}],
        qconnections=[{
            "node1": "r2",
            "node2": "r3",
            "attenuation": 0,
            "distance": 1000,
            "type": "meet_in_the_middle",
        }],
        cconnections=[{"node1": "r2", "node2": "r3", "delay": int(1e9)}],
    )

    tl = topo.get_timeline()
    print(f"stop_time overridden to: {tl.stop_time:.0e}")

    routers = topo.get_nodes_by_type("InstrumentedRouter")
    bsm_nodes = topo.get_nodes_by_type(BSM_NODE)
    print(f"InstrumentedRouter nodes: {[r.name for r in routers]}")
    print(f"Auto-generated BSM nodes: {[b.name for b in bsm_nodes]}")

    tl.init()
    tl.run()

    print("\nEntanglement generation attempts per router:")
    for r in sorted(routers, key=lambda n: n.name):
        print(f"  {r.name}: {r.eg_attempt_count}")
