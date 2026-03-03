"""Demo — programmatic topology construction with a custom router node.

This is the simplest extension path:
1. subclass a built-in node that already fits the network family
2. register it under a new name
3. use that name directly in the topology build_config
"""

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.node import Node, QuantumRouter
from sequence.topology.const_topo import BSM_NODE


@Node.register("YbRouterNode")
class YbRouterNode(QuantumRouter):
    """QuantumRouter with a few Yb-specific labels for demo purposes."""

    platform = "Yb"
    operating_wavelength = 980


if __name__ == "__main__":
    topo = RouterNetTopo(
        {
            "nodes": [
                {"name": "yb_a", "type": "YbRouterNode", "seed": 0, "memo_size": 5},
                {"name": "yb_b", "type": "YbRouterNode", "seed": 1, "memo_size": 5},
            ],
            "qconnections": [
                {
                    "node1": "yb_a",
                    "node2": "yb_b",
                    "attenuation": 0,
                    "distance": 1000,
                    "type": "meet_in_the_middle",
                    "seed": 2,
                },
            ],
            "cconnections": [
                {"node1": "yb_a", "node2": "yb_b", "delay": int(1e9)},
            ],
            "stop_time": 10e12,
        }
    )

    routers = topo.get_nodes_by_type("YbRouterNode")
    print("Custom routers:", [(node.name, node.platform, node.operating_wavelength) for node in routers])
    print("Generated BSM nodes:", [node.name for node in topo.get_nodes_by_type(BSM_NODE)])
