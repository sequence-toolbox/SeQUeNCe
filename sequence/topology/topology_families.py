"""Concrete TopologyFamily subclasses.

All base topology-family behaviors live here. To add a new topology family,
either define a new TopologyFamily subclass for entirely new behavior, or
subclass BsmTopologyFamily or QlanTopologyFamily to build on their shared behavior.
Register the chosen family in the relevant topology file.
"""
from abc import ABC

from networkx import Graph, dijkstra_path, exception

from ..network_management.routing_distributed import DistributedRoutingProtocol
from ..network_management.routing_static import StaticRoutingProtocol

from .qlan.orchestrator import QlanOrchestratorNode
from .qlan.client import QlanClientNode
from .node import Node, BSMNode, QuantumRouter, DQCNode
from .const_topo import (
    ALL_NODE, ALL_Q_CHANNEL, ALL_C_CHANNEL,
    ATTENUATION, BSM_NODE, QUANTUM_ROUTER, DQC_NODE,
    CONNECT_NODE_1, CONNECT_NODE_2,
    DELAY, DISTANCE, MEET_IN_THE_MID,
    NAME, SEED, SRC, DST, TEMPLATE, TYPE,
    ORCHESTRATOR, CLIENT,
    LOCAL_MEMORIES, CLIENT_NUMBER, MEASUREMENT_BASES,
    MEM_FIDELITY_ORCH, MEM_FREQUENCY_ORCH, MEM_EFFICIENCY_ORCH,
    MEM_COHERENCE_ORCH, MEM_WAVELENGTH_ORCH,
    MEM_FIDELITY_CLIENT, MEM_FREQUENCY_CLIENT, MEM_EFFICIENCY_CLIENT,
    MEM_COHERENCE_CLIENT, MEM_WAVELENGTH_CLIENT,
)
class TopologyFamily(ABC):
    """Abstract base for topology-family behavior.

    Each concrete subclass owns the infrastructure for one family of topologies
    (BSM-based nets, QLAN, etc.). Topology delegates its variable pipeline steps
    here via composition rather than inheritance.

    Most methods are no-op defaults. Topologies that use the shared _add_nodes
    pipeline must supply a family with a real _build_node implementation.
    Concrete implementations live in topology_families.py.
    """

    def _configure_family(self, config: dict, templates: dict) -> None: pass

    def _attach_protocols(self) -> None: pass

    def _prepare_build_state(self, config: dict, bsm_to_router_map: dict) -> None: pass

    def _wire_post_nodes(self, bsm_to_router_map: dict, tl) -> None: pass

    def _expand_qconnection(self, q_connect: dict, cc_delay: float, config: dict) -> None: pass

    def _generate_forwarding_table(self, config: dict, nodes: dict, qchannels: list) -> None: pass

    def _order_nodes(self, node_list: list) -> list:
        return node_list

    def _build_node(self, node: dict, node_type: str, template: dict,
                    tl, nodes: dict, bsm_to_router_map: dict) -> None:
        """Construct node, call set_seed, append to nodes[node_type].

        Family subclassers using the shared _add_nodes pipeline must
        implement this method.

        Args:
            node (dict): one entry from build_config[ALL_NODE].
            node_type (str): the TYPE string for this node.
            template (dict): resolved template dict for this node (may be empty).
            tl (Timeline): simulation timeline.
            nodes (dict): topology's nodes defaultdict - append here.
            bsm_to_router_map (dict): BSM-to-router name mapping (used by BsmTopologyFamily).
        """
        raise NotImplementedError(
            "TopologyFamily does not build nodes by default. "
            "The topology must override _add_nodes or provide a family with _build_node."
        )

class BsmTopologyFamily(TopologyFamily):
    """Implementor for networks with midpoint infrastructure and routing.

    Used by RouterNetTopo and DQCNetTopo. Owns midpoint node auto-creation
    (currently BSMNode, extensible to other midpoint hardware),
    endpoint-to-midpoint wiring, and forwarding table generation.
    """

    def _midpoint_type_for_qconnection(self, q_connect: dict) -> str:
        return BSM_NODE

    # NOTE: upstream only differed on router-vs-DQC midpoint naming; both were auto-generated.
    # We currently treat `.auto` as the unified naming policy unless compatibility says otherwise.
    def _midpoint_name_for_qconnection(self, node1: str, node2: str, q_connect: dict) -> str:
        return f"BSM.{node1}.{node2}.auto"

    # NOTE: keep qconnection expansion policy small unless a real second expansion
    # shape lands. The current midpoint/channel artifact hooks cover known extension
    # needs; avoid splitting _expand_qconnection further without a concrete use case.

    def _is_routing_endpoint_type(self, node_type: str) -> bool:
        return node_type in (QUANTUM_ROUTER, DQC_NODE)

    def _midpoint_node_config(self, node1: str, node2: str, q_connect: dict) -> dict:
        return {
            NAME: self._midpoint_name_for_qconnection(node1, node2, q_connect),
            TYPE: self._midpoint_type_for_qconnection(q_connect),
            SEED: q_connect.get(SEED, 0),
            TEMPLATE: q_connect.get(TEMPLATE, None),
        }

    def _qchannel_configs_for_qconnection(self, node1: str, node2: str,
                                           midpoint_name: str, q_connect: dict) -> list[dict]:
        attenuation = q_connect[ATTENUATION]
        distance = q_connect[DISTANCE] // 2
        return [
            {
                NAME: f"QC.{src}.{midpoint_name}",
                SRC: src,
                DST: midpoint_name,
                DISTANCE: distance,
                ATTENUATION: attenuation,
            }
            for src in (node1, node2)
        ]

    def _cchannel_configs_for_qconnection(self, node1: str, node2: str,
                                           midpoint_name: str, cc_delay: float,
                                           q_connect: dict) -> list[dict]:
        distance = q_connect[DISTANCE] // 2
        cchannels = []
        for src in (node1, node2):
            cchannels.append({
                NAME: f"CC.{src}.{midpoint_name}",
                SRC: src,
                DST: midpoint_name,
                DISTANCE: distance,
                DELAY: cc_delay,
            })
            cchannels.append({
                NAME: f"CC.{midpoint_name}.{src}",
                SRC: midpoint_name,
                DST: src,
                DISTANCE: distance,
                DELAY: cc_delay,
            })
        return cchannels

    def _prepare_build_state(self, config: dict, bsm_to_router_map: dict) -> None:
        node_types = {node[NAME]: node[TYPE] for node in config[ALL_NODE]}
        for qc in config.get(ALL_Q_CHANNEL, []):
            src, dst = qc[SRC], qc[DST]
            if node_types.get(dst, "") != BSM_NODE:
                continue
            if dst in bsm_to_router_map:
                bsm_to_router_map[dst].append(src)
            else:
                bsm_to_router_map[dst] = [src]

    def _wire_post_nodes(self, bsm_to_router_map: dict, tl) -> None:
        for bsm in bsm_to_router_map:
            if len(bsm_to_router_map[bsm]) != 2:
                raise ValueError(f"BSM midpoint {bsm} must connect to exactly 2 endpoints")
            r0_str, r1_str = bsm_to_router_map[bsm]
            r0 = tl.get_entity_by_name(r0_str)
            r1 = tl.get_entity_by_name(r1_str)
            if r0 is not None:
                r0.add_bsm_node(bsm, r1_str)
            if r1 is not None:
                r1.add_bsm_node(bsm, r0_str)

    def _expand_qconnection(self, q_connect: dict, cc_delay: float, config: dict) -> None:
        node1        = q_connect[CONNECT_NODE_1]
        node2        = q_connect[CONNECT_NODE_2]
        channel_type = q_connect[TYPE]

        if channel_type == MEET_IN_THE_MID:
            midpoint = self._midpoint_node_config(node1, node2, q_connect)
            midpoint_name = midpoint[NAME]
            config[ALL_NODE].append(midpoint)
            qchannels = self._qchannel_configs_for_qconnection(node1, node2, midpoint_name, q_connect)
            if qchannels:
                if ALL_Q_CHANNEL not in config:
                    config[ALL_Q_CHANNEL] = []
                config[ALL_Q_CHANNEL].extend(qchannels)
            cchannels = self._cchannel_configs_for_qconnection(
                node1, node2, midpoint_name, cc_delay, q_connect
            )
            if cchannels:
                if ALL_C_CHANNEL not in config:
                    config[ALL_C_CHANNEL] = []
                config[ALL_C_CHANNEL].extend(cchannels)
        else:
            raise NotImplementedError(f"Unknown quantum connection type '{channel_type}'")

    # nodes.items() is filtered for endpoints multiple times in this function.
    # Could extract endpoint nodes once at the top if this method grows further.
    def _generate_forwarding_table(self, config: dict, nodes: dict, qchannels: list) -> None:
        graph = Graph()
        for node in config[ALL_NODE]:
            if self._is_routing_endpoint_type(node[TYPE]):
                graph.add_node(node[NAME])

        costs = {}
        for qc in qchannels:
            router, bsm = qc.sender.name, qc.receiver
            if bsm not in costs:
                costs[bsm] = [router, qc.distance]
            else:
                costs[bsm] = [router] + costs[bsm]
                costs[bsm][-1] += qc.distance
        # Routing protocols live on endpoint nodes only - midpoint nodes have no network manager.
        routing_protocol = None
        for node_type, node_list in nodes.items():
            if self._is_routing_endpoint_type(node_type):
                routing_protocol = node_list[0].network_manager.get_routing_protocol()
                break

        if isinstance(routing_protocol, StaticRoutingProtocol):
            graph.add_weighted_edges_from(costs.values())
            for node_type, node_list in nodes.items():
                if not self._is_routing_endpoint_type(node_type):
                    continue
                for src in node_list:
                    for dst_name in graph.nodes:
                        if src.name == dst_name:
                            continue
                        try:
                            if dst_name > src.name:
                                path = dijkstra_path(graph, src.name, dst_name)
                            else:
                                path = dijkstra_path(graph, dst_name, src.name)[::-1]
                            next_hop = path[1]
                            # routing protocol locates at the bottom of the stack
                            routing_protocol = src.network_manager.get_routing_protocol()
                            routing_protocol.add_forwarding_rule(dst_name, next_hop)
                        except exception.NetworkXNoPath:
                            pass

        elif isinstance(routing_protocol, DistributedRoutingProtocol):
            # distributed routing, initialize the link cost and setup the FSM
            for node_type, node_list in nodes.items():
                if not self._is_routing_endpoint_type(node_type):
                    continue
                for q_router in node_list:
                    routing_protocol: DistributedRoutingProtocol = q_router.network_manager.get_routing_protocol()
                    for bsm, cost_info in costs.items():
                        if q_router.name in cost_info:
                            neighbor = cost_info[0] if cost_info[0] != q_router.name else cost_info[1]
                            cost = cost_info[2]
                            routing_protocol.link_cost[neighbor] = cost
    
    def _build_node(self, node: dict, node_type: str, template: dict,
                    tl, nodes: dict, bsm_to_router_map: dict) -> None:
        # NOTE: if/elif dispatch on centralized type constants from const_topo.py.
        # A follow-up PR (issue #241) will replace this with registry-based construction.
        if node_type == BSM_NODE:
            others = bsm_to_router_map.get(node[NAME], [])
            node_obj = BSMNode(node[NAME], tl, others, component_templates=template)
        elif node_type == QUANTUM_ROUTER:
            memo_size = node.get("memo_size", 0)
            node_obj = QuantumRouter(node[NAME], tl, memo_size, component_templates=template)
        elif node_type == DQC_NODE:
            memo_size = node.get("memo_size", 0)
            data_memo_size = node.get("data_memo_size", 0)
            node_obj = DQCNode(node[NAME], tl, memo_size=memo_size, data_memo_size=data_memo_size, component_templates=template)
        else:
            raise ValueError(f"Unknown node type '{node_type}'")
        node_obj.set_seed(node[SEED])
        nodes[node_type].append(node_obj)

class QlanTopologyFamily(TopologyFamily):
    """Implementor for QLAN star topologies.

    Owns QLAN-specific parameter reading (dual flat/template format),
    node ordering (clients before orchestrator), and node construction.
    """

    def _configure_family(self, config: dict, templates: dict) -> None:
        """Detect build_config format, normalize memory params, and init per-node accumulators.

        Supports two formats (legacy flat keys and new template-based) independently
        for orchestrator and client nodes. Writes normalized params into
        self.orch_component_templates / self.client_component_templates as
        {"MemoryArray": {...}} dicts so _build_node can pass them straight through
        to node constructors via component_templates.
        """
        # Structural params
        self.n_local_memories = config.get(LOCAL_MEMORIES, 1)
        self.n_clients        = config.get(CLIENT_NUMBER, 1)
        self.meas_bases       = config.get(MEASUREMENT_BASES, 'z')

        # LEGACY: flat top-level memory params.
        # Older configs specified fidelity, frequency, etc. as top-level keys.
        # New configs use per-node templates instead. These branches are backwards compat only.
        self.orch_component_templates   = None
        self.client_component_templates = None

        if MEM_FIDELITY_ORCH in config:
            self.orch_component_templates = {"MemoryArray": {
                "fidelity":       config.get(MEM_FIDELITY_ORCH,   0.9),
                "frequency":      config.get(MEM_FREQUENCY_ORCH,  2000),
                "efficiency":     config.get(MEM_EFFICIENCY_ORCH, 1),
                "coherence_time": config.get(MEM_COHERENCE_ORCH,  -1),
                "wavelength":     config.get(MEM_WAVELENGTH_ORCH, 500),
            }}

        if MEM_FIDELITY_CLIENT in config:
            self.client_component_templates = {"MemoryArray": {
                "fidelity":       config.get(MEM_FIDELITY_CLIENT,   0.9),
                "frequency":      config.get(MEM_FREQUENCY_CLIENT,  2000),
                "efficiency":     config.get(MEM_EFFICIENCY_CLIENT, 1),
                "coherence_time": config.get(MEM_COHERENCE_CLIENT,  -1),
                "wavelength":     config.get(MEM_WAVELENGTH_CLIENT, 500),
            }}

        # Accumulator lists - populated by _build_node
        self._remote_memories      = []
        self.orchestrator_nodes    = []
        self.client_nodes          = []
        self.remote_memories_array = []

    def _order_nodes(self, node_list: list) -> list:
        """Sort clients before orchestrators so single-pass construction works.

        By the time _build_node hits an orchestrator, all client Memory objects
        already exist in self._remote_memories.
        """
        clients       = [n for n in node_list if n[TYPE] == CLIENT]
        orchestrators = [n for n in node_list if n[TYPE] == ORCHESTRATOR]
        others        = [n for n in node_list if n[TYPE] not in (CLIENT, ORCHESTRATOR)]
        return others + clients + orchestrators

    def _attach_protocols(self) -> None:
        """Wire measurement and correction protocols on all QLAN nodes."""
        for orch in self.orchestrator_nodes:
            orch.resource_manager.create_protocol()
        for client in self.client_nodes:
            client.resource_manager.create_protocol()

    def _register_client_node(self, node_obj: Node) -> None:
        """Track client state needed for orchestrator construction and public API."""
        memo = node_obj.get_components_by_type("MemoryArray")[0][0]
        self._remote_memories.append(memo)
        self.remote_memories_array.append(memo)
        self.client_nodes.append(node_obj)

    def _register_orchestrator_node(self, node_obj: Node) -> None:
        """Track orchestrator nodes exposed on the topology API."""
        self.orchestrator_nodes.append(node_obj)

    def _build_node(self, node: dict, node_type: str, template: dict,
                    tl, nodes: dict, bsm_to_router_map: dict) -> None:
        """Construct QLAN nodes."""
        # NOTE: if/elif dispatch on centralized type constants from const_topo.py.
        # A follow-up PR (issue #241) will replace this with registry-based construction.
        if node_type == CLIENT:
            node_obj = QlanClientNode(node[NAME], tl, 1,
                                      component_templates=self.client_component_templates or template)
            self._register_client_node(node_obj)

        elif node_type == ORCHESTRATOR:
            node_obj = QlanOrchestratorNode(node[NAME], tl, self.n_local_memories,
                                            self._remote_memories,
                                            component_templates=self.orch_component_templates or template)
            node_obj.update_bases(self.meas_bases)
            self._register_orchestrator_node(node_obj)

        else:
            raise ValueError(f"Unknown QLAN node type '{node_type}'")

        node_obj.set_seed(node[SEED])
        nodes[node_type].append(node_obj)
