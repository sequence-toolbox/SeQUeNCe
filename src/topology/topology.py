"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to manage a network's structure.
Topology instances automatically perform many useful network functions.
"""
from abc import abstractmethod
from typing import TYPE_CHECKING, Dict

import json5

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel


class Topology():
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
        self.nodes = {}
        self.qchannels = []
        self.cchannels = []
        self.tl = None
        self._load(conf_file_name)

    @abstractmethod
    def _load(self, filename):
        pass

    def _add_qchannels(self, config):
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

    def _add_cchannels(self, config):
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

    def _add_cconnections(self, config):
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

    def get_nodes_by_type(self, type: str):
        return self.nodes[type]

    def get_qchannels(self) -> List["QuantumChannel"]:
        return self.qchannels

    def get_cchannels(self) -> List["ClassicalChannel"]:
        return self.cchannels

    def get_nodes(self) -> Dict[str, List["Node"]]:
        return self.nodes
