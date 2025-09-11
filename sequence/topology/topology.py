"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel
from . import topology_constants as tc


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

    @abstractmethod
    def _load(self, filename: str):
        """Method for parsing configuration file and generate network

        Args:
            filename (str): the name of configuration file
        """
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
