"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""

import json
import warnings
import numpy as np

from abc import ABC, ABCMeta
from collections import defaultdict

from ..kernel.timeline import Timeline
from ..kernel.quantum_manager import KET_STATE_FORMALISM, QuantumManager

from .network_impls import NetworkImpl
from .node import Node
from .const_topo import (
    ALL_C_CONNECT, ALL_C_CHANNEL, ALL_NODE, ALL_Q_CONNECT, ALL_Q_CHANNEL,
    ATTENUATION, CONNECT_NODE_1, CONNECT_NODE_2, DELAY, DISTANCE, DST,
    NAME, SEED, SRC, STOP_TIME, TRUNC, TYPE, ALL_TEMPLATES, TEMPLATE,
    GATE_FIDELITY, MEASUREMENT_FIDELITY, FORMALISM,
)
from ..components.optical_channel import QuantumChannel, ClassicalChannel
from ..constants import SPEED_OF_LIGHT


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
        bsm_to_router_map (dict): mapping BSM nodes to router nodes.
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
    
    def __init__(self, conf_file_name: str, networkimpl: NetworkImpl):
        """Build a network topology from a config file (.json or .yaml).

        Args:
            conf_file_name (str): path to a .json or .yaml/.yml config file
            networkimpl (NetworkImpl): composed implementor for this topology family
        """
        if not conf_file_name.endswith(('.json', '.yaml', '.yml')):
            raise ValueError(
                f"Unsupported config file format: {conf_file_name}. "
                "Use .json or .yaml/.yml"
            )
        with open(conf_file_name) as fh:
            if conf_file_name.endswith(('.yaml', '.yml')):
                import yaml
                config = yaml.safe_load(fh)
            else:
                config = json.load(fh)

        self._setup(config, networkimpl)
        self._raw_cfg = config

    def _setup(self, config: dict, networkimpl: NetworkImpl) -> None:
        """Execute the full build pipeline on a config dict.

        Separated from __init__ so CreateTopo can supply a programmatically
        built config dict instead of a file.
        """
        self.bsm_to_router_map = {}
        self.nodes: dict[str, list[Node]] = defaultdict(list)
        self.qchannels: list[QuantumChannel] = []
        self.cchannels: list[ClassicalChannel] = []
        self.templates: dict[str, dict] = {}
        self.tl: Timeline | None = None
        self._impl = networkimpl

        self._get_templates(config)
        self._configure_parameters(config)
        self._add_qconnections(config)
        self._add_timeline(config)
        self._impl._map_bsm_routers(config, self.bsm_to_router_map)
        self._add_nodes(config)
        self._impl._add_bsm_node_to_router(self.bsm_to_router_map, self.tl)
        self._add_qchannels(config)
        self._add_cchannels(config)
        self._add_cconnections(config)
        self._impl._generate_forwarding_table(config, self.nodes, self.qchannels)
        self._add_protocols()

    def _add_nodes(self, config: dict):
        ordered_configs = self._impl._ordered_node_dicts(config[ALL_NODE])
        for node_config in ordered_configs:
            node_type = node_config[TYPE]
            template  = self.templates.get(node_config.get(TEMPLATE), {})
            self._impl._create_node(node_config, node_type, template,
                                    self.tl, self.nodes, self.bsm_to_router_map)

    def _configure_parameters(self, config: dict):
        self._impl._configure_parameters(config, self.templates)

    def _add_protocols(self):
        self._impl._add_protocols()

    def _get_templates(self, config: dict) -> None:
        self.templates = config.get(ALL_TEMPLATES, {})

    def _add_timeline(self, config: dict):
        stop_time = config.get(STOP_TIME, float('inf'))
        formalism = config.get(FORMALISM, KET_STATE_FORMALISM)
        truncation = config.get(TRUNC, 1)
        QuantumManager.set_global_manager_formalism(formalism)
        self.tl = Timeline(stop_time=stop_time, truncation=truncation)

    def _calc_cc_delay(self, config: dict, node1: str, node2: str) -> float:
        """Return the one-way classical channel delay between node1 and node2.

        Args:
            config (dict): full topology configuration dictionary.
            node1 (str): name of the first node.
            node2 (str): name of the second node.
        """
        cc_delay = []
        for cc in config.get(ALL_C_CHANNEL, []):
            if ((cc[SRC] == node1 and cc[DST] == node2)
                    or (cc[SRC] == node2 and cc[DST] == node1)):
                cc_delay.append(cc.get(DELAY, cc.get(DISTANCE, 1000) / SPEED_OF_LIGHT))

        for cc in config.get(ALL_C_CONNECT, []):
            if ((cc[CONNECT_NODE_1] == node1 and cc[CONNECT_NODE_2] == node2)
                    or (cc[CONNECT_NODE_1] == node2 and cc[CONNECT_NODE_2] == node1)):
                cc_delay.append(cc.get(DELAY, cc.get(DISTANCE, 1000) / SPEED_OF_LIGHT))

        assert len(cc_delay) > 0, (
            f"No classical channel/connection found between {node1} and {node2}"
        )
        return np.mean(cc_delay) // 2

    def _add_qconnections(self, config: dict) -> None:
        for q_connect in config.get(ALL_Q_CONNECT, []):
            node1    = q_connect[CONNECT_NODE_1]
            node2    = q_connect[CONNECT_NODE_2]
            cc_delay = int(self._calc_cc_delay(config, node1, node2))
            self._impl._handle_qconnection(q_connect, cc_delay, config)

    def _add_qchannels(self, config: dict) -> None:
        for qc in config.get(ALL_Q_CHANNEL, []):
            src_str, dst_str = qc[SRC], qc[DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = qc.get(NAME, f"qc-{src_str}-{dst_str}")
                qc_obj = QuantumChannel(name, self.tl, qc[ATTENUATION], qc[DISTANCE])
                qc_obj.set_ends(src_node, dst_str)
                self.qchannels.append(qc_obj)

    def _add_cchannels(self, config: dict) -> None:
        for cc in config.get(ALL_C_CHANNEL, []):
            self._make_classical_channel(
                cc[SRC], cc[DST],
                cc.get(DISTANCE, -1), cc.get(DELAY, -1),
                name=cc.get(NAME),
            )

    def _add_cconnections(self, config: dict) -> None:
        for c in config.get(ALL_C_CONNECT, []):
            distance = c.get(DISTANCE, -1)
            delay    = c.get(DELAY, -1)
            for src_str, dst_str in zip(
                [c[CONNECT_NODE_1], c[CONNECT_NODE_2]],
                [c[CONNECT_NODE_2], c[CONNECT_NODE_1]],
            ):
                self._make_classical_channel(src_str, dst_str, distance, delay)

    def _make_classical_channel(self, src_str: str, dst_str: str,
                                 distance: float, delay: float,
                                 name: str = None) -> None:
        src_obj = self.tl.get_entity_by_name(src_str)
        if src_obj is not None:
            cc_obj = ClassicalChannel(
                name or f"cc-{src_str}-{dst_str}",
                self.tl, distance, delay,
            )
            cc_obj.set_ends(src_obj, dst_str)
            self.cchannels.append(cc_obj)

    def get_timeline(self) -> "Timeline":
        if self.tl is None:
            raise RuntimeError("Timeline is not set — topology may not be fully initialised.")
        return self.tl

    def get_nodes_by_type(self, type: str) -> list[Node]:
        return self.nodes[type]

    def get_qchannels(self) -> list["QuantumChannel"]:
        return self.qchannels

    def get_cchannels(self) -> list["ClassicalChannel"]:
        return self.cchannels

    def get_nodes(self) -> dict[str, list["Node"]]:
        return self.nodes
