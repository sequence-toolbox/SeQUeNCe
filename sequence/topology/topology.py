"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""

import json
import warnings
from abc import ABC, ABCMeta, abstractmethod
from collections import defaultdict
from ..kernel.timeline import Timeline

from .node import *
from .const_topo import (
    ALL_C_CONNECT, ALL_C_CHANNEL, ALL_NODE, ALL_Q_CONNECT, ALL_Q_CHANNEL,
    ATTENUATION, CONNECT_NODE_1, CONNECT_NODE_2, DELAY, DISTANCE, DST,
    NAME, SEED, SRC, STOP_TIME, TRUNC, TYPE, ALL_TEMPLATES, TEMPLATE,
    GATE_FIDELITY, MEASUREMENT_FIDELITY, FORMALISM,
)
from ..components.optical_channel import QuantumChannel, ClassicalChannel


class _DeprecatedAttrMeta(ABCMeta):
    """Metaclass that warns when deprecated class attributes are accessed.

    Each class using this metaclass can define a _deprecated_attrs dict
    mapping old attribute names to their values. The metaclass walks the
    MRO to find the right dict.
    """

    def __getattr__(cls, name):
        for klass in cls.__mro__:
            deprecated = klass.__dict__.get("_deprecated_attrs", {})
            if name in deprecated:
                warnings.warn(
                    f"Accessing {cls.__name__}.{name} is deprecated. "
                    f"Use 'from sequence.topology.const_topo import {name}' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return deprecated[name]
        raise AttributeError(
            f"type object {cls.__name__!r} has no attribute {name!r}"
        )


class Topology(ABC, metaclass=_DeprecatedAttrMeta):
    """Class for generating network from configuration file.

    The topology class provides a simple interface for managing the nodes
    and connections in a network.
    A network may also be generated using an external json file.

    Attributes:
        bsm router-to-map
        nodes (dict[str, list[Node]]): mapping of type of node to a list of same type node.
        qchannels (list[QuantumChannel]): list of quantum channel objects in network.
        cchannels (list[ClassicalChannel]): list of classical channel objects in network.
        tl (Timeline): the timeline used for simulation
    """

    _deprecated_attrs = {
        "ALL_C_CONNECT": ALL_C_CONNECT,
        "ALL_C_CHANNEL": ALL_C_CHANNEL,
        "ALL_NODE": ALL_NODE,
        "ALL_Q_CONNECT": ALL_Q_CONNECT,
        "ALL_Q_CHANNEL": ALL_Q_CHANNEL,
        "ATTENUATION": ATTENUATION,
        "CONNECT_NODE_1": CONNECT_NODE_1,
        "CONNECT_NODE_2": CONNECT_NODE_2,
        "DELAY": DELAY,
        "DISTANCE": DISTANCE,
        "DST": DST,
        "NAME": NAME,
        "SEED": SEED,
        "SRC": SRC,
        "STOP_TIME": STOP_TIME,
        "TRUNC": TRUNC,
        "TYPE": TYPE,
        "ALL_TEMPLATES": ALL_TEMPLATES,
        "TEMPLATE": TEMPLATE,
        "GATE_FIDELITY": GATE_FIDELITY,
        "MEASUREMENT_FIDELITY": MEASUREMENT_FIDELITY,
        "FORMALISM": FORMALISM,
    }

    def __init__(self, conf_file_name: str):
        """Constructor for topology class.

        Args:
            conf_file_name (str): the name of configuration file
        """
        self.bsm_to_router_map = {}

        self.nodes: dict[str, list[Node]] = defaultdict(list)
        self.qchannels: list[QuantumChannel] = []
        self.cchannels: list[ClassicalChannel] = []
        self.templates: dict[str, dict] = {}
        self.tl: Timeline | None = None

        with open(conf_file_name) as fh:
            config = json.load(fh)

        self._get_templates(config)
        self._add_parameters(config)
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

    #NOTE: figure out some sort of enum matching for this so that right networks get the right treatment
    #so far that just means that if it isn't QunatumRepeater or DQC it doesn't mean anything
    def _generate_forwarding_table(self, config: dict):
        pass

    #ofc all child classes must have ts
    @abstractmethod
    def _add_nodes(self, config: dict):
        pass

    #NOTE: most quantum networks should have qconnections but just in case, don't enforce
    def _add_qconnections(self, config: dict) -> None:
        """Pass because not all networks have to have qconnections"""
        pass

    #NOTE:make this not enforced
    def _add_parameters(self, config: dict):
        pass
    

    def _get_templates(self, config: dict) -> None:
        templates = config.get(ALL_TEMPLATES, {})
        self.templates = templates


    def _add_timeline(self, config: dict):
        stop_time = config.get(STOP_TIME, float('inf'))
        self.tl = Timeline(stop_time)
        #NOTE maybe add something for wtv turns 


    def _map_bsm_routers(self, config):
        pass

    def _add_bsm_node_to_router(self):
        pass


    def _add_qchannels(self, config: dict) -> None:
        for qc in config.get(ALL_Q_CHANNEL, []):
            src_str, dst_str = qc[SRC], qc[DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = qc.get(NAME, f"qc-{src_str}-{dst_str}")
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
                name = cc.get(NAME, f"cc-{src_str}-{dst_str}")
                distance = cc.get(DISTANCE, -1)
                delay = cc.get(DELAY, -1)
                cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                cc_obj.set_ends(src_node, dst_str)
                self.cchannels.append(cc_obj)


    def _add_cconnections(self, config: dict) -> None:
        for c_connect in config.get(ALL_C_CONNECT, []):
            node1 = c_connect[CONNECT_NODE_1]
            node2 = c_connect[CONNECT_NODE_2]
            distance = c_connect.get(DISTANCE, -1)
            delay = c_connect.get(DELAY, -1)
            for src_str, dst_str in zip([node1, node2], [node2, node1]):
                name = f"cc-{src_str}-{dst_str}"
                src_obj = self.tl.get_entity_by_name(src_str)
                if src_obj is not None:
                    cc_obj = ClassicalChannel(name, self.tl, distance, delay)
                    cc_obj.set_ends(src_obj, dst_str)
                    self.cchannels.append(cc_obj)

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

