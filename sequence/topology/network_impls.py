"""Concrete NetworkImpl subclasses.

All topology implementors live here. To add a new topology family,
add a new NetworkImpl subclass and register it in the relevant topology file.
"""
from abc import ABC, abstractmethod

from .qlan.orchestrator import QlanOrchestratorNode
from .qlan.client import QlanClientNode

from networkx import Graph, dijkstra_path, exception

from ..network_management.routing_distributed import DistributedRoutingProtocol
from ..network_management.routing_static import StaticRoutingProtocol

from .node import Node, BSMNode, QuantumRouter
from .const_topo import (
    ALL_NODE, ALL_Q_CHANNEL, ALL_C_CHANNEL,
    ATTENUATION, BSM_NODE, CONNECT_NODE_1, CONNECT_NODE_2,
    DELAY, DISTANCE, MEET_IN_THE_MID,
    MEMO_ARRAY_SIZE, DATA_MEMO_ARRAY_SIZE,
    NAME, SEED, SRC, DST, TEMPLATE, TYPE,
    ORCHESTRATOR, CLIENT,
    QUANTUM_ROUTER, DQC_NODE,
    LOCAL_MEMORIES, CLIENT_NUMBER, MEASUREMENT_BASES,
    MEM_FIDELITY_ORCH, MEM_FREQUENCY_ORCH, MEM_EFFICIENCY_ORCH,
    MEM_COHERENCE_ORCH, MEM_WAVELENGTH_ORCH,
    MEM_FIDELITY_CLIENT, MEM_FREQUENCY_CLIENT, MEM_EFFICIENCY_CLIENT,
    MEM_COHERENCE_CLIENT, MEM_WAVELENGTH_CLIENT,
)

# NOTE: consider grouping node-type and midpoint-type constants into sets/enums here
#       so impls that switch on node_type have an obvious checklist to maintain.

class NetworkImpl(ABC):
    """Abstract base for topology implementors.

    Each concrete subclass owns the infrastructure for one family of topologies
    (BSM-based nets, QLAN, etc.). Topology delegates its variable pipeline steps
    here via composition rather than inheritance.

    All methods are no-op defaults except _create_node which every impl must define.
    Concrete implementations live in network_impls.py.
    """

    def _configure_parameters(self, config: dict, templates: dict) -> None: pass

    def _add_protocols(self) -> None: pass

    def _map_bsm_routers(self, config: dict, bsm_to_router_map: dict) -> None: pass

    def _add_bsm_node_to_router(self, bsm_to_router_map: dict, tl) -> None: pass

    def _handle_qconnection(self, q_connect: dict, cc_delay: float, config: dict) -> None: pass

    def _generate_forwarding_table(self, config: dict, nodes: dict, qchannels: list) -> None: pass

    def _ordered_node_dicts(self, node_list: list) -> list:
        return node_list

    @abstractmethod
    def _create_node(self, node: dict, node_type: str, template: dict,
                     tl, nodes: dict, bsm_to_router_map: dict) -> None:
        """Construct node, call set_seed, append to nodes[node_type].

        Args:
            node (dict): one entry from config[ALL_NODE].
            node_type (str): the TYPE string for this node.
            template (dict): resolved template dict for this node (may be empty).
            tl (Timeline): simulation timeline.
            nodes (dict): topology's nodes defaultdict - append here.
            bsm_to_router_map (dict): BSM-to-router name mapping (used by BsmNetworkImpl).
        """
        pass


class NoOpNetworkImpl(NetworkImpl):
    """Minimal impl for topologies that manage their own node creation.

    Used when the topology does not need BSM/QLAN infrastructure.
    """

    def _create_node(self, node, node_type, template,
                     tl, nodes, bsm_to_router_map) -> None:
        raise NotImplementedError(
            "NoOpNetworkImpl does not create nodes. "
            "The topology must override _add_nodes itself."
        )


class BsmNetworkImpl(NetworkImpl):
    """Implementor for networks with midpoint infrastructure and routing.

    Used by RouterNetTopo and DQCNetTopo. Owns midpoint node auto-creation
    (currently BSMNode, extensible to QFC+BSM and other hardware),
    endpoint-to-midpoint wiring, and forwarding table generation.
    """


    def _map_bsm_routers(self, config: dict, bsm_to_router_map: dict) -> None:
        for qc in config[ALL_Q_CHANNEL]:
            src, dst = qc[SRC], qc[DST]
            if dst in bsm_to_router_map:
                bsm_to_router_map[dst].append(src)
            else:
                bsm_to_router_map[dst] = [src]

    def _add_bsm_node_to_router(self, bsm_to_router_map: dict, tl) -> None:
        for bsm in bsm_to_router_map:
            r0_str, r1_str = bsm_to_router_map[bsm]
            r0 = tl.get_entity_by_name(r0_str)
            r1 = tl.get_entity_by_name(r1_str)
            if r0 is not None:
                r0.add_bsm_node(bsm, r1_str)
            if r1 is not None:
                r1.add_bsm_node(bsm, r0_str)

    def _handle_qconnection(self, q_connect: dict, cc_delay: float, config: dict) -> None:
        node1        = q_connect[CONNECT_NODE_1]
        node2        = q_connect[CONNECT_NODE_2]
        attenuation  = q_connect[ATTENUATION]
        distance     = q_connect[DISTANCE] // 2
        channel_type = q_connect[TYPE]

        if channel_type == MEET_IN_THE_MID:
            # Auto-generate a midpoint BSM node and its quantum/classical channels.
            # The .auto suffix distinguishes these from manually specified BSM nodes in the config.
            bsm_name = f"BSM.{node1}.{node2}.auto"
            config[ALL_NODE].append({
                NAME:     bsm_name,
                TYPE:     BSM_NODE,
                SEED:     q_connect.get(SEED, 0),
                TEMPLATE: q_connect.get(TEMPLATE, None),
            })
            for src in [node1, node2]:
                config.setdefault(ALL_Q_CHANNEL, []).append({
                    NAME: f"QC.{src}.{bsm_name}", SRC: src,
                    DST: bsm_name, DISTANCE: distance, ATTENUATION: attenuation,
                })
                config.setdefault(ALL_C_CHANNEL, []).append({
                    NAME: f"CC.{src}.{bsm_name}", SRC: src,
                    DST: bsm_name, DISTANCE: distance, DELAY: cc_delay,
                })
                config[ALL_C_CHANNEL].append({
                    NAME: f"CC.{bsm_name}.{src}", SRC: bsm_name,
                    DST: src, DISTANCE: distance, DELAY: cc_delay,
                })
        else:
            raise NotImplementedError(f"Unknown quantum connection type '{channel_type}'")

    # nodes.items() is filtered for endpoints multiple times in this function.
    # could extract endpoint_nodes once at the top - check with whoever last touched this before changing.
    def _generate_forwarding_table(self, config: dict, nodes: dict, qchannels: list) -> None:
        graph = Graph()
        for node in config[ALL_NODE]:
            if node[TYPE] != BSM_NODE:
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
            if node_type != BSM_NODE:
                routing_protocol = node_list[0].network_manager.get_routing_protocol()
                break

        if isinstance(routing_protocol, StaticRoutingProtocol):
            graph.add_weighted_edges_from(costs.values())
            for node_type, node_list in nodes.items():
                if node_type == BSM_NODE:
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
                if node_type == BSM_NODE:
                    continue
                for q_router in node_list:
                    routing_protocol: DistributedRoutingProtocol = q_router.network_manager.get_routing_protocol()
                    for bsm, cost_info in costs.items():
                        if q_router.name in cost_info:
                            neighbor = cost_info[0] if cost_info[0] != q_router.name else cost_info[1]
                            cost = cost_info[2]
                            routing_protocol.link_cost[neighbor] = cost
    
    def _create_node(self, node: dict, node_type: str, template: dict,
                      tl, nodes: dict, bsm_to_router_map: dict) -> None:
        others = bsm_to_router_map.get(node[NAME], [])
        node_obj = Node.create(node_type, node[NAME], tl, node, template, others=others)
        node_obj.set_seed(node[SEED])
        nodes[node_type].append(node_obj)


class QlanNetworkImpl(NetworkImpl):
    """Implementor for QLAN star topologies.

    Owns QLAN-specific parameter reading (dual flat/template format),
    node ordering (clients before orchestrator), and node construction.
    """

    def _configure_parameters(self, config: dict, templates: dict) -> None:
        """Detect config format, normalize memory params, and init per-node accumulators.

        Supports two formats (legacy flat keys and new template-based) independently
        for orchestrator and client nodes. Writes normalized params into
        self.orch_component_templates / self.client_component_templates as
        {"MemoryArray": {...}} dicts so _create_node can pass them straight through
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

        # Accumulator lists - populated by _create_node
        self._remote_memories      = []
        self.orchestrator_nodes    = []
        self.client_nodes          = []
        self.remote_memories_array = []

    def _ordered_node_dicts(self, node_list: list) -> list:
        """Sort clients before orchestrators so single-pass construction works.

        By the time _create_node hits an orchestrator, all client Memory objects
        already exist in self._remote_memories.
        """
        clients       = [n for n in node_list if n[TYPE] == CLIENT]
        orchestrators = [n for n in node_list if n[TYPE] == ORCHESTRATOR]
        others        = [n for n in node_list if n[TYPE] not in (CLIENT, ORCHESTRATOR)]
        return others + clients + orchestrators

    def _add_protocols(self) -> None:
        """Wire measurement and correction protocols on all QLAN nodes."""
        for orch in self.orchestrator_nodes:
            orch.resource_manager.create_protocol()
        for client in self.client_nodes:
            client.resource_manager.create_protocol()

    def _create_node(self, node: dict, node_type: str, template: dict,
                     tl, nodes: dict, bsm_to_router_map: dict) -> None:
        """Construct QLAN nodes."""
        if node_type == CLIENT:
            node_obj = Node.create(node_type, node[NAME], tl, node, template,
                                   component_templates=self.client_component_templates)
            node_obj.set_seed(node[SEED])
            memo = node_obj.get_components_by_type("MemoryArray")[0][0]
            self._remote_memories.append(memo)
            self.remote_memories_array.append(memo)
            self.client_nodes.append(node_obj)

        elif node_type == ORCHESTRATOR:
            node_obj = Node.create(node_type, node[NAME], tl, node, template,
                                   component_templates=self.orch_component_templates,
                                   n_local_memories=self.n_local_memories,
                                   remote_memories=self._remote_memories)
            node_obj.update_bases(self.meas_bases)
            node_obj.set_seed(node[SEED])
            self.orchestrator_nodes.append(node_obj)

        else:
            node_obj = Node.create(node_type, node[NAME], tl, node, template)
            node_obj.set_seed(node[SEED])

        nodes[node_type].append(node_obj)

