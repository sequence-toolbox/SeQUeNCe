"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""
from abc import abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel


class Topology:
    """Class for generating network from configuration file.

    The topology class provides a simple interface for managing the nodes
    and connections in a network.
    A network may also be generated using an external json file.

    Attributes:
        nodes (Dict[str, List[Node]]): mapping of type of node to a list of same type node.
        qchannels (List[QuantumChannel]): list of quantum channel objects in network.
        cchannels (List[ClassicalChannel]): list of classical channel objects in network.
        tl (Timeline): the timeline used for simulation
    """

    ALL_CC_CONNECT = "cconnections"
    ALL_C_CHANNEL = "cchannels"
    ALL_NODE = "nodes"
    ALL_QC_CONNECT = "qconnections"
    ALL_Q_CHANNEL = "qchannels"
    ATTENUATION = "attenuation"
    CONNECT_NODE_1 = "node1"
    CONNECT_NODE_2 = "node2"
    DELAY = "delay"
    DISTANCE = "distance"
    DST = "destination"
    NAME = "name"
    SEED = "seed"
    SRC = "source"
    STOP_TIME = "stop_time"
    TYPE = "type"

    def __init__(self, conf_file_name: str):
        """Constructor for topology class.

        Args:
            conf_file_name (str): the name of configuration file
        """
        self.nodes: Dict[str, List[Node]] = defaultdict(lambda: [])
        self.qchannels: List[QuantumChannel] = []
        self.cchannels: List[ClassicalChannel] = []
        self.tl: Optional[Timeline] = None
        self._load(conf_file_name)

    @abstractmethod
    def _load(self, filename: str):
        """Method for parsing configuration file and generate network

        Args:
            filename (str): the name of configuration file
        """
        pass

    def _add_qchannels(self, config: Dict) -> None:
        for qc in config.get(self.ALL_Q_CHANNEL, []):
            src_str, dst_str = qc[self.SRC], qc[self.DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = qc.get(self.NAME, "qc.{}.{}".format(src_str, dst_str))
                distance = qc[self.DISTANCE]
                attenuation = qc[self.ATTENUATION]
                qc_obj = QuantumChannel(name, self.tl, attenuation, distance)
                qc_obj.set_ends(src_node, dst_str)
                self.qchannels.append(qc_obj)

    def _add_cchannels(self, config: Dict) -> None:
        for cc in config.get(self.ALL_C_CHANNEL, []):
            src_str, dst_str = cc[self.SRC], cc[self.DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = cc.get(self.NAME, "cc.{}.{}".format(src_str, dst_str))
                distance = cc.get(self.DISTANCE, 1000)
                delay = cc.get(self.DELAY, -1)
                cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                cc_obj.set_ends(src_node, dst_str)
                self.cchannels.append(cc_obj)

    def _add_cconnections(self, config: Dict) -> None:
        for c_connect in config.get(self.ALL_CC_CONNECT, []):
            node1 = c_connect[self.CONNECT_NODE_1]
            node2 = c_connect[self.CONNECT_NODE_2]
            distance = c_connect.get(self.DISTANCE, 1000)
            delay = c_connect.get(self.DELAY, -1)
            for src_str, dst_str in zip([node1, node2], [node2, node1]):
                name = "cc.{}.{}".format(src_str, dst_str)
                src_obj = self.tl.get_entity_by_name(src_str)
                if src_obj is not None:
                    cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                    cc_obj.set_ends(src_obj, dst_str)
                    self.cchannels.append(cc_obj)

    def get_timeline(self) -> "Timeline":
        assert self.tl is not None, "timeline is not set properly."
        return self.tl

    def get_nodes_by_type(self, type: str) -> List[Node]:
        return self.nodes[type]

    def get_qchannels(self) -> List["QuantumChannel"]:
        return self.qchannels

    def get_cchannels(self) -> List["ClassicalChannel"]:
        return self.cchannels

    def get_nodes(self) -> Dict[str, List["Node"]]:
        return self.nodes
