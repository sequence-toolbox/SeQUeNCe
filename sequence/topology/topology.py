"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""
import json
from abc import ABC
from collections import defaultdict

import yaml
from networkx import Graph, dijkstra_path, exception

from . import topology_constants as tc
from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel
from ..constants import KET_STATE_FORMALISM
from ..kernel.quantum_manager import QuantumManager
from ..kernel.timeline import Timeline


class Topology(ABC):
    """Class for generating network from configuration file.

    The topology class provides a simple interface for managing the nodes
    and connections in a network.
    A network may also be generated using an external json file.

    Attributes:
        nodes (dict[str, list[Node]]): mapping of type of node to a list of same type node.
        qchannels (list[QuantumChannel]): list of quantum channel objects in network.
        cchannels (list[ClassicalChannel]): list of classical channel objects in network.
        tl (Timeline): the timeline used for simulation
    """
    
    def __init__(self, conf_file_name: str):
        """Constructor for topology class.

        Args:
            conf_file_name (str): the name of configuration file
        """
        self.nodes: dict[str, list[Node]] = defaultdict(list)
        self.qchannels: list[QuantumChannel] = []
        self.cchannels: list[ClassicalChannel] = []
        self.templates: dict[str, dict] = {}
        self.tl: Timeline | None = None
        self._load(conf_file_name)

    def _load(self, filename: str):
        """Method for parsing configuration file and generate network

        Defines the standard control flow

        Args:
            filename (str): the name of configuration file
        """
        # Load the config.
        config = self._load_json(filename)
        self._get_templates(config)

        # Preprocess (HOOK)
        self._pre_hook(config)

        # Create the timeline
        self.tl = self._create_timeline(config)

        # Nodes (HOOK)
        self._node_setup_hook(config)

        # Channels
        self._add_qchannels(config)
        self._add_cchannels(config)

        # Connections
        self._add_cconnections(config)

        # Setup routing
        self._post_hook(config)


    def _pre_hook(self, config: dict) -> None:
        """Preprocess hook for topology setup."""
        pass

    def _node_setup_hook(self, config: dict) -> None:
        """Node setup hook for topology setup."""
        pass

    def _post_hook(self, config: dict) -> None:
        """Postprocess hook for topology setup."""
        pass

    @staticmethod
    def _create_timeline(config):
        stop_time = config.get(tc.STOP_TIME, 10 ** 23)
        formalism = config.get(tc.FORMALISM, KET_STATE_FORMALISM)
        truncation = config.get(tc.TRUNC, 1)
        QuantumManager.set_global_manager_formalism(formalism)
        if config.get(tc.IS_PARALLEL, False):
            raise Exception("Please install 'psequence' package for parallel simulations.")
        else:
            timeline = Timeline(stop_time=stop_time, truncation=truncation)
        return timeline

    @staticmethod
    def _load_json(filename: str) -> dict:
        if filename.endswith(".json"):
            with open(filename) as f:
                return json.load(f)
        elif filename.endswith(('.yaml', '.yml')):
            with open(filename) as f:
                return yaml.safe_load(f)

    def _add_nodes(self, config: dict) -> None:
        pass



    def _get_templates(self, config: dict) -> None:
        templates = config.get(tc.ALL_TEMPLATES, {})
        self.templates = templates

    def _add_qchannels(self, config: dict) -> None:
        for qc in config.get(tc.ALL_Q_CHANNEL, []):
            src_str, dst_str = qc[tc.SRC], qc[tc.DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = qc.get(tc.NAME, f"qc.{src_str}.{dst_str}")
                distance = qc[tc.DISTANCE]
                attenuation = qc[tc.ATTENUATION]
                qc_obj = QuantumChannel(name, self.tl, attenuation, distance)
                qc_obj.set_ends(src_node, dst_str)
                self.qchannels.append(qc_obj)

    def _add_cchannels(self, config: dict) -> None:
        for cc in config.get(tc.ALL_C_CHANNEL, []):
            src_str, dst_str = cc[tc.SRC], cc[tc.DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = cc.get(tc.NAME, f"cc.{src_str}.{dst_str}")
                distance = cc.get(tc.DISTANCE, 1000)
                delay = cc.get(tc.DELAY, -1)
                cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                cc_obj.set_ends(src_node, dst_str)
                self.cchannels.append(cc_obj)

    def _add_cconnections(self, config: dict) -> None:
        for c_connect in config.get(tc.ALL_C_CONNECT, []):
            node1 = c_connect[tc.CONNECT_NODE_1]
            node2 = c_connect[tc.CONNECT_NODE_2]
            distance = c_connect.get(tc.DISTANCE, 1000)
            delay = c_connect.get(tc.DELAY, -1)
            for src_str, dst_str in zip([node1, node2], [node2, node1]):
                name = f"cc.{src_str}.{dst_str}"
                src_obj = self.tl.get_entity_by_name(src_str)
                if src_obj is not None:
                    cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                    cc_obj.set_ends(src_obj, dst_str)
                    self.cchannels.append(cc_obj)


    def _generate_forwarding_table(self, config: dict, node_type: str):
        """For static routing."""
        graph = Graph()
        for node in config[tc.ALL_NODE]:
            if node[tc.TYPE] == node_type:
                graph.add_node(node[tc.NAME])

        costs = {}
        if config[tc.IS_PARALLEL]:
            for qc in config[tc.ALL_Q_CHANNEL]:
                router, bsm = qc[tc.SRC], qc[tc.DST]
                if bsm not in costs:
                    costs[bsm] = [router, qc[tc.DISTANCE]]
                else:
                    costs[bsm] = [router] + costs[bsm]
                    costs[bsm][-1] += qc[tc.DISTANCE]
        else:
            for qc in self.qchannels:
                router, bsm = qc.sender.name, qc.receiver
                if bsm not in costs:
                    costs[bsm] = [router, qc.distance]
                else:
                    costs[bsm] = [router] + costs[bsm]
                    costs[bsm][-1] += qc.distance

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
                    # routing protocol locates at the bottom of the stack
                    routing_protocol = src.network_manager.protocol_stack[0]  # guarantee that [0] is the routing protocol?
                    routing_protocol.add_forwarding_rule(dst_name, next_hop)
                except exception.NetworkXNoPath:
                    pass

    def get_timeline(self) -> "Timeline":
        assert self.tl is not None, "timeline is not set properly."
        return self.tl

    def get_nodes_by_type(self, type: str) -> list[Node]:
        return self.nodes[type]

    def get_qchannels(self) -> list["QuantumChannel"]:
        return self.qchannels

    def get_cchannels(self) -> list["ClassicalChannel"]:
        return self.cchannels

    def get_nodes(self) -> dict[str, list["Node"]]:
        return self.nodes
