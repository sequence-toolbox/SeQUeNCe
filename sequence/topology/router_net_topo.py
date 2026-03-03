"""RouterNetTopo — quantum router entanglement distribution network topology."""

from .topology import Topology
from .topology_families import BsmTopologyFamily

from .const_topo import (
    BSM_NODE, CONTROLLER, MEET_IN_THE_MID, MEMO_ARRAY_SIZE,
    PORT, PROC_NUM, QUANTUM_ROUTER,
)


class RouterNetTopo(Topology):
    """Topology for quantum entanglement distribution networks using quantum routers.

    Nodes: QuantumRouter (end nodes), BSMNode (auto-created at link midpoints).
    Supports static and distributed routing protocols.

    Attributes:
        nodes (dict[str, list[Node]]): mapping of node type to list of nodes.
        qchannels (list[QuantumChannel]): quantum channels in the network.
        cchannels (list[ClassicalChannel]): classical channels in the network.
        tl (Timeline): simulation timeline.
    """

    _deprecated_attrs = {
        "BSM_NODE":       BSM_NODE,
        "MEET_IN_THE_MID": MEET_IN_THE_MID,
        "MEMO_ARRAY_SIZE": MEMO_ARRAY_SIZE,
        "PORT":           PORT,
        "PROC_NUM":       PROC_NUM,
        "QUANTUM_ROUTER": QUANTUM_ROUTER,
        "CONTROLLER":     CONTROLLER,
    }

    # Add topo-specific member functions here, e.g. querying, inference, aggregation

    def __init__(self, config: "str | dict", **kwargs):
        super().__init__(config, BsmTopologyFamily(), **kwargs)
