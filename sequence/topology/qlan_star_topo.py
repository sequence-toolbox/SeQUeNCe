"""QlanStarTopo — QLAN star topology with one orchestrator and multiple clients."""

from .topology import Topology
from .network_impls import QlanNetworkImpl

from .const_topo import (
    CLIENT, CLIENT_NUMBER, LOCAL_MEMORIES, MEASUREMENT_BASES, MEET_IN_THE_MID,
    MEM_COHERENCE_CLIENT, MEM_COHERENCE_ORCH,
    MEM_EFFICIENCY_CLIENT, MEM_EFFICIENCY_ORCH,
    MEM_FIDELITY_CLIENT, MEM_FIDELITY_ORCH,
    MEM_FREQUENCY_CLIENT, MEM_FREQUENCY_ORCH,
    MEMO_ARRAY_SIZE, MEM_WAVELENGTH_CLIENT, MEM_WAVELENGTH_ORCH,
    ORCHESTRATOR,
)


class QlanStarTopo(Topology):
    """Topology for QLAN networks with a single orchestrator and multiple clients.

    Entanglement is generated abstractly (linear chain graph state injected directly).
    No BSM nodes. No routing table.

    Attributes:
        orchestrator_nodes (list[QlanOrchestratorNode]): orchestrator nodes.
        client_nodes (list[QlanClientNode]): client nodes.
        remote_memories_array (list[Memory]): client memory objects.
        nodes (dict[str, list[Node]]): mapping of node type to list of nodes.
        qchannels (list[QuantumChannel]): quantum channels in the network.
        cchannels (list[ClassicalChannel]): classical channels in the network.
        tl (Timeline): simulation timeline.
    """

    _deprecated_attrs = {
        "MEET_IN_THE_MID":      MEET_IN_THE_MID,
        "ORCHESTRATOR":         ORCHESTRATOR,
        "CLIENT":               CLIENT,
        "LOCAL_MEMORIES":       LOCAL_MEMORIES,
        "CLIENT_NUMBER":        CLIENT_NUMBER,
        "MEM_FIDELITY_ORCH":    MEM_FIDELITY_ORCH,
        "MEM_FREQUENCY_ORCH":   MEM_FREQUENCY_ORCH,
        "MEM_EFFICIENCY_ORCH":  MEM_EFFICIENCY_ORCH,
        "MEM_COHERENCE_ORCH":   MEM_COHERENCE_ORCH,
        "MEM_WAVELENGTH_ORCH":  MEM_WAVELENGTH_ORCH,
        "MEM_FIDELITY_CLIENT":  MEM_FIDELITY_CLIENT,
        "MEM_FREQUENCY_CLIENT": MEM_FREQUENCY_CLIENT,
        "MEM_EFFICIENCY_CLIENT": MEM_EFFICIENCY_CLIENT,
        "MEM_COHERENCE_CLIENT": MEM_COHERENCE_CLIENT,
        "MEM_WAVELENGTH_CLIENT": MEM_WAVELENGTH_CLIENT,
        "MEASUREMENT_BASES":    MEASUREMENT_BASES,
        "MEM_SIZE":             MEMO_ARRAY_SIZE,  # MEM_SIZE was a duplicate of MEMO_ARRAY_SIZE, consolidated here
    }

    def __init__(self, config: "str | dict", **kwargs):
        impl = QlanNetworkImpl()
        super().__init__(config, impl, **kwargs)
        # Expose impl state as topology attributes for public API
        self.orchestrator_nodes    = impl.orchestrator_nodes
        self.client_nodes          = impl.client_nodes
        self.remote_memories_array = impl.remote_memories_array
        self.n_local_memories      = impl.n_local_memories
        self.n_clients             = impl.n_clients
        self.meas_bases            = impl.meas_bases
        # Hardware memo params (fidelity, frequency, etc.) cannot be read off the topo directly.

