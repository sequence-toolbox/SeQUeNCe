"""Topology package — network construction and configuration.

Public API:
    RouterNetTopo  — BSM-based router networks (entanglement distribution)
    DQCNetTopo     — distributed quantum computing networks
    QlanStarTopo   — QLAN star topology (orchestrator + clients)
    QKDTopo        — quantum key distribution networks
    Topology       — base class (usable directly with a TopologyFamily)
    Node           — base node class with type registry
"""

__all__ = [
    'topology',
    'node',
    'const_topo',
    'topology_families',
    'router_net_topo',
    'dqc_net_topo',
    'qlan_star_topo',
    'qkd_topo',
]

def __dir__():
    return sorted(__all__)
