"""DQCNetTopo — distributed quantum computing network topology."""

from .topology import Topology
from .topology_families import BsmTopologyFamily

from .const_topo import (
    ALL_NODE, BSM_NODE, CONTROLLER, DATA_MEMO_ARRAY_SIZE,
    DQC_NODE, MEET_IN_THE_MID, MEMO_ARRAY_SIZE, ROLE_DQC_ENDPOINT,
)


class DqcBsmFamily(BsmTopologyFamily):
    """BSM implementor for distributed quantum computing networks."""

    def _is_routing_endpoint_type(self, node_type: str) -> bool:
        return self._type_has_role(node_type, ROLE_DQC_ENDPOINT)


class DQCNetTopo(Topology):
    """Topology for distributed quantum computing networks.

    Nodes: DQCNode (compute endpoints with data + communication memories),
    BSMNode (auto-created at link midpoints).
    Supports static routing only.

    Attributes:
        nodes (dict[str, list[Node]]): mapping of node type to list of nodes.
        qchannels (list[QuantumChannel]): quantum channels in the network.
        cchannels (list[ClassicalChannel]): classical channels in the network.
        tl (Timeline): simulation timeline.
    """

    _deprecated_attrs = {
        "BSM_NODE":            BSM_NODE,
        "MEET_IN_THE_MID":     MEET_IN_THE_MID,
        "MEMO_ARRAY_SIZE":     MEMO_ARRAY_SIZE,
        "CONTROLLER":          CONTROLLER,
        "DQC_NODE":            DQC_NODE,
        "DATA_MEMO_ARRAY_SIZE": DATA_MEMO_ARRAY_SIZE,
    }

    def __init__(self, config: "str | dict", **kwargs):
        super().__init__(config, DqcBsmFamily(), **kwargs)

    def infer_qubit_to_node(self, total_wires: int) -> dict[int, str]:
        """Auto-infer the {wire_index: node_name} map by assigning every node's
        n_data qubits in JSON order.

        Args:
            total_wires (int): total number of wires (qubits) in the circuit.
        Returns:
            dict[int, str]: mapping from wire index to node name.
        """
        mapping: dict[int, str] = {}
        next_wire = 0
        for nd in self._input_cfg[ALL_NODE]:
            name   = nd["name"]
            n_data = nd.get("n_data", 1)
            for _ in range(n_data):
                if next_wire >= total_wires:
                    raise ValueError(f"Mapping overflow: more data qubits than {total_wires}")
                mapping[next_wire] = name
                next_wire += 1
        if next_wire != total_wires:
            raise ValueError(f"Configured for {next_wire} wires but circuit has {total_wires}")
        return mapping

    def infer_memory_owners(self, total_wires: int,
                            ancilla_inds: list[int]) -> dict[str, dict[int, int]]:
        """Return data_owners: node_name → {wire_index: slot_index_in_memory_array}.

        Args:
            total_wires (int): total number of wires (qubits) in the circuit.
            ancilla_inds (list[int]): ancilla qubit indices (reserved for future use).

        Returns:
            dict[str, dict[int, int]]: node_name → {wire_index: slot_index_in_memory_array}.
        """
        qubit_to_node = self.infer_qubit_to_node(total_wires)
        data_owners: dict[str, dict[int, int]] = {
            node_name: {} for node_name in dict.fromkeys(qubit_to_node.values())
        }
        for q, owner in qubit_to_node.items():
            slot = len(data_owners[owner])
            data_owners[owner][q] = slot
        return data_owners
