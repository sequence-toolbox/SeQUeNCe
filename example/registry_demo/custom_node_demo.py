"""Registry pattern demo: custom node + custom network manager.

This example shows how to extend SeQUeNCe without touching any core files.
We define a custom NetworkManager that tracks rule generation, and a custom
QuantumRouter that uses it — both registered and wired together entirely in
user space.

Run with:
    python example/registry_demo/custom_node_demo.py
"""

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.node import Node, QuantumRouter
from sequence.network_management.network_manager import NetworkManager, DistributedNetworkManager
from sequence.network_management.reservation import Reservation


# --- 1. Custom NetworkManager -------------------------------------------
# Subclass the default distributed manager and add rule generation logging.

@NetworkManager.register("logging")
class LoggingNetworkManager(DistributedNetworkManager):
    """Network manager that logs every rule generation event."""

    def __init__(self, owner, memory_array_name, **kwargs):
        super().__init__(owner, memory_array_name, **kwargs)
        self.rule_count = 0

    def generate_rules(self, reservation: Reservation):
        self.rule_count += 1
        print(f"[{self.owner.name}] rule generation #{self.rule_count}: "
              f"{reservation.initiator} -> {reservation.responder}")
        super().generate_rules(reservation)


# --- 2. Custom Node --------------------------------------------------------
# Subclass QuantumRouter and swap in the logging manager after construction.

@Node.register("LoggingRouter")
class LoggingRouter(QuantumRouter):
    """QuantumRouter that uses LoggingNetworkManager."""

    def __init__(self, name, tl, memo_size=50, seed=None,
                 component_templates={}, gate_fid=1, meas_fid=1):
        super().__init__(name, tl, memo_size, seed, component_templates, gate_fid, meas_fid)
        self.network_manager = LoggingNetworkManager(
            self, self.memo_arr_name, component_templates=component_templates
        )

    @classmethod
    def from_config(cls, name, tl, config, template, **kwargs):
        memo_size = config.get("memo_size", 0)
        return cls(name, tl, memo_size, component_templates=template)


# --- 3. Run the simulation -------------------------------------------------

if __name__ == "__main__":
    topo = RouterNetTopo("example/registry_demo/demo_config.json")
    tl = topo.get_timeline()
    tl.show_progress = False

    routers = topo.get_nodes_by_type("LoggingRouter")
    assert len(routers) == 2, "Expected 2 LoggingRouter nodes"

    node1, node2 = sorted(routers, key=lambda n: n.name)

    from sequence.app.request_app import RequestApp
    app = RequestApp(node1)
    app.start(node2.name, start_t=int(1e12), end_t=int(10e12),
              memo_size=5, fidelity=0.5)

    tl.init()
    tl.run()

    print(f"\nRule generation counts:")
    for r in routers:
        print(f"  {r.name}: {r.network_manager.rule_count} reservation(s)")
