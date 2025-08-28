"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Optional, Any
import json

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel


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

    ALL_C_CONNECT = "cconnections"    # a connection consist of two opposite direction channels
    ALL_C_CHANNEL = "cchannels"
    ALL_NODE = "nodes"
    ALL_Q_CONNECT = "qconnections"
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
    ALL_TEMPLATES = "templates"
    TEMPLATE = "template"
    GATE_FIDELITY = "gate_fidelity"
    MEASUREMENT_FIDELITY = "measurement_fidelity"

    
    def __init__(self, config: [str, dict[str, Any]]):
        """Constructor for topology class.

        Args:
            config (str, dict): if str, interpreted as name of JSON configuration file.
                if dict, interpreted as already loaded configuration dictionary.
        """
        self.nodes: dict[str, list[Node]] = defaultdict(list)
        self.qchannels: list[QuantumChannel] = []
        self.cchannels: list[ClassicalChannel] = []
        self.templates: dict[str, dict] = {}
        self.tl: Optional[Timeline] = None

        if type(config) is str:
            with open(config, "r") as f:
                config = json.load(f)
        self._load(config)

    @abstractmethod
    def _load(self, config: dict[str, Any]) -> None:
        """Method for parsing configuration and generating network

        Args:
            config (dict): configuration dictionary
        """
        pass

    def _get_templates(self, config: dict) -> None:
        templates = config.get(Topology.ALL_TEMPLATES, {})
        self.templates = templates

    def _add_qchannels(self, config: dict) -> None:
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

    def _add_cchannels(self, config: dict) -> None:
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

    def _add_cconnections(self, config: dict) -> None:
        for c_connect in config.get(self.ALL_C_CONNECT, []):
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

    def get_nodes_by_type(self, type: str) -> list[Node]:
        return self.nodes[type]

    def get_qchannels(self) -> list["QuantumChannel"]:
        return self.qchannels

    def get_cchannels(self) -> list["ClassicalChannel"]:
        return self.cchannels

    def get_nodes(self) -> dict[str, list["Node"]]:
        return self.nodes
