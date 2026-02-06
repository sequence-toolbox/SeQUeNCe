"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""
import json
from abc import ABC, abstractmethod
from collections import defaultdict

import numpy as np
import yaml

from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel
from ..constants import *


class Topology(ABC):
    """Class for generating network from configuration file.

    The topology class provides a simple interface for managing the nodes
    and connections in a network.
    A network may also be generated using an external JSON or YAML file.

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
        """Load configuration file and build the network.

        Handles both JSON and YAML config files. Calls _get_templates()
        then delegates to child's _build() method.

        Args:
            filename: path to the configuration file (JSON or YAML)
        """
        config = self._load_config(filename)
        self._get_templates(config)
        self._build(config)

    def _load_config(self, filename: str) -> dict:
        """Load configuration from JSON or YAML file.

        Args:
            filename: path to the configuration file

        Returns:
            Configuration dictionary
        """
        with open(filename) as fh:
            if filename.endswith(('.yaml', '.yml')):
                return yaml.safe_load(fh)
            return json.load(fh)

    @abstractmethod
    def _build(self, config: dict):
        """Build the network from configuration.

        Child classes implement this to create nodes, channels, etc.

        Args:
            config: configuration dictionary
        """
        pass

    def _get_templates(self, config: dict) -> None:
        templates = config.get(ALL_TEMPLATES, {})
        self.templates = templates

    def _add_timeline(self, config: dict):
        stop_time = config.get(STOP_TIME, float('inf'))
        self.tl = Timeline(stop_time)

    def _calc_cc_delay(self, config: dict, node1: str, node2: str) -> float:
        """get the classical channel delay between two nodes from the config"""
        cc_delay = []
        for cc in config.get(ALL_C_CHANNEL, []):
            if (cc[SRC] == node1 and cc[DST] == node2) \
                    or (cc[SRC] == node2 and cc[DST] == node1):
                delay = cc.get(DELAY, cc.get(DISTANCE, 1000) / SPEED_OF_LIGHT)
                cc_delay.append(delay)

        for cc in config.get(ALL_C_CONNECT, []):
            if (cc[CONNECT_NODE_1] == node1 and cc[CONNECT_NODE_2] == node2) \
                    or (cc[CONNECT_NODE_1] == node2 and cc[CONNECT_NODE_2] == node1):
                delay = cc.get(DELAY, cc.get(DISTANCE, 1000) / SPEED_OF_LIGHT)
                cc_delay.append(delay)

        assert len(cc_delay) > 0, \
            f"No classical channel/connection found between {node1} and {node2}"
        return np.mean(cc_delay) // 2

    def _add_qchannels(self, config: dict) -> None:
        for qc in config.get(ALL_Q_CHANNEL, []):
            src_str, dst_str = qc[SRC], qc[DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = qc.get(NAME, f"qc.{src_str}.{dst_str}")
                distance = qc[DISTANCE]
                attenuation = qc[ATTENUATION]
                qc_obj = QuantumChannel(name, self.tl, attenuation, distance)
                qc_obj.set_ends(src_node, dst_str)
                self.qchannels.append(qc_obj)

    def _add_cchannels(self, config: dict) -> None:
        for cc in config.get(ALL_C_CHANNEL, []):
            src_str, dst_str = cc[SRC], cc[DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = cc.get(NAME, f"cc.{src_str}.{dst_str}")
                distance = cc.get(DISTANCE, 1000)
                delay = cc.get(DELAY, -1)
                cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                cc_obj.set_ends(src_node, dst_str)
                self.cchannels.append(cc_obj)

    def _add_cconnections(self, config: dict) -> None:
        for c_connect in config.get(ALL_C_CONNECT, []):
            node1 = c_connect[CONNECT_NODE_1]
            node2 = c_connect[CONNECT_NODE_2]
            distance = c_connect.get(DISTANCE, 1000)
            delay = c_connect.get(DELAY, -1)
            for src_str, dst_str in zip([node1, node2], [node2, node1]):
                name = f"cc.{src_str}.{dst_str}"
                src_obj = self.tl.get_entity_by_name(src_str)
                if src_obj is not None:
                    cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                    cc_obj.set_ends(src_obj, dst_str)
                    self.cchannels.append(cc_obj)

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
