"""Definition of the MultihopTopo class.

MultihopTopo is a child class of Topology that provides a base for
implementing multi-hop topologies with BSM nodes and forwarding tables.

Current subclasses: RouterNetTopo, DQCNetTopo
"""
from abc import abstractmethod

from networkx import Graph, dijkstra_path, exception

from .topology import Topology
from ..kernel.timeline import Timeline
from ..kernel.quantum_manager import KET_STATE_FORMALISM, QuantumManager
from ..network_management.routing_distributed import DistributedRoutingProtocol
from ..network_management.routing_static import StaticRoutingProtocol
from ..constants import *


class MultihopTopo(Topology):
    """Subclasses MUST define:
        _add_nodes()
        class attributes _BSM_NAME_TEMPLATE and _ROUTER_NODE_TYPE.

    Attributes:
        bsm_to_router_map (dict[str, list[str]]): mapping of BSM node name to its two connected routers.
        encoding_type: encoding type for the network.
    """

    _BSM_NAME_TEMPLATE = "BSM.{}.{}"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "_ROUTER_NODE_TYPE" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must define _ROUTER_NODE_TYPE"
            )

    def __init__(self, conf_file_name: str):
        self.bsm_to_router_map = {}
        self.encoding_type = None
        super().__init__(conf_file_name)

    def _build(self, config: dict):
        # quantum connections are only supported by sequential simulation so far
        self._add_qconnections(config)
        self._add_timeline(config)
        self._map_bsm_routers(config)
        self._add_nodes(config)
        self._add_bsm_node_to_router()
        self._add_qchannels(config)
        self._add_cchannels(config)
        self._add_cconnections(config)
        self._generate_forwarding_table(config)

    def _add_timeline(self, config: dict):
        stop_time = config.get(STOP_TIME, 10 ** 23)
        formalism = config.get(FORMALISM, KET_STATE_FORMALISM)
        truncation = config.get(TRUNC, 1)
        QuantumManager.set_global_manager_formalism(formalism)
        self.tl = Timeline(stop_time=stop_time, truncation=truncation)

    def _map_bsm_routers(self, config):
        for qc in config.get(ALL_Q_CHANNEL, []):
            src, dst = qc[SRC], qc[DST]
            if dst in self.bsm_to_router_map:
                self.bsm_to_router_map[dst].append(src)
            else:
                self.bsm_to_router_map[dst] = [src]

    def _add_bsm_node_to_router(self):
        for bsm in self.bsm_to_router_map:
            r0_str, r1_str = self.bsm_to_router_map[bsm]
            r0 = self.tl.get_entity_by_name(r0_str)
            r1 = self.tl.get_entity_by_name(r1_str)
            if r0 is not None:
                r0.add_bsm_node(bsm, r1_str)
            if r1 is not None:
                r1.add_bsm_node(bsm, r0_str)

    def _add_qconnections(self, config: dict):
        """generate bsm_info, qc_info, and cc_info for the q_connections."""
        for q_connect in config.get(ALL_Q_CONNECT, []):
            node1 = q_connect[CONNECT_NODE_1]
            node2 = q_connect[CONNECT_NODE_2]
            attenuation = q_connect[ATTENUATION]
            distance = q_connect[DISTANCE] // 2
            channel_type = q_connect[TYPE]
            cc_delay = self._calc_cc_delay(config, node1, node2)

            if channel_type == MEET_IN_THE_MID:
                bsm_name = self._BSM_NAME_TEMPLATE.format(node1, node2)
                bsm_seed = q_connect.get(SEED, 0)
                bsm_template_name = q_connect.get(TEMPLATE, None)
                bsm_info = {NAME: bsm_name,
                            TYPE: BSM_NODE,
                            SEED: bsm_seed,
                            TEMPLATE: bsm_template_name}
                config[ALL_NODE].append(bsm_info)

                for src in [node1, node2]:
                    qc_name = f"QC.{src}.{bsm_name}"  # the quantum channel
                    qc_info = {NAME: qc_name,
                               SRC: src,
                               DST: bsm_name,
                               DISTANCE: distance,
                               ATTENUATION: attenuation}
                    if ALL_Q_CHANNEL not in config:
                        config[ALL_Q_CHANNEL] = []
                    config[ALL_Q_CHANNEL].append(qc_info)

                    cc_name = f"CC.{src}.{bsm_name}"  # the classical channel
                    cc_info = {NAME: cc_name,
                               SRC: src,
                               DST: bsm_name,
                               DISTANCE: distance,
                               DELAY: cc_delay}
                    if ALL_C_CHANNEL not in config:
                        config[ALL_C_CHANNEL] = []
                    config[ALL_C_CHANNEL].append(cc_info)

                    cc_name = f"CC.{bsm_name}.{src}"
                    cc_info = {NAME: cc_name,
                               SRC: bsm_name,
                               DST: src,
                               DISTANCE: distance,
                               DELAY: cc_delay}
                    config[ALL_C_CHANNEL].append(cc_info)
            else:
                raise NotImplementedError("Unknown type of quantum connection")

    @abstractmethod
    def _add_nodes(self, config: dict):
        pass

    def _generate_forwarding_table(self, config: dict):
        """Generate forwarding table for each router."""
        node_type = self._ROUTER_NODE_TYPE

        graph = Graph()
        for node in config[ALL_NODE]:
            if node[TYPE] == node_type:
                graph.add_node(node[NAME])

        costs = {}
        for qc in self.qchannels:
            router, bsm = qc.sender.name, qc.receiver
            if bsm not in costs:
                costs[bsm] = [router, qc.distance]
            else:
                costs[bsm] = [router] + costs[bsm]
                costs[bsm][-1] += qc.distance

        # check which routing protocol is in use
        routing_protocol = None
        for q_router in self.nodes[node_type]:
            routing_protocol = q_router.network_manager.get_routing_protocol()
            break

        if isinstance(routing_protocol, StaticRoutingProtocol):
            graph.add_weighted_edges_from(costs.values())
            for src in self.nodes[node_type]:
                for dst_name in graph.nodes:
                    if src.name == dst_name:
                        continue
                    try:
                        if dst_name > src.name:
                            path = dijkstra_path(graph, src.name, dst_name)
                        else:
                            path = dijkstra_path(graph, dst_name, src.name)[::-1]
                        next_hop = path[1]
                        routing_protocol = src.network_manager.get_routing_protocol()
                        routing_protocol.add_forwarding_rule(dst_name, next_hop)
                    except exception.NetworkXNoPath:
                        pass

        elif isinstance(routing_protocol, DistributedRoutingProtocol):
            for q_router in self.nodes[node_type]:
                routing_protocol: DistributedRoutingProtocol = q_router.network_manager.get_routing_protocol()
                for bsm, cost_info in costs.items():
                    if q_router.name in cost_info:
                        neighbor = cost_info[0] if cost_info[0] != q_router.name else cost_info[1]
                        cost = cost_info[2]
                        routing_protocol.link_cost[neighbor] = cost
                routing_protocol.init()

        elif routing_protocol is not None:
            raise NotImplementedError(
                f"Unsupported routing protocol: {type(routing_protocol).__name__}"
            )
