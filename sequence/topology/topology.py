"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to
manage a network's structure.
Topology instances automatically perform many useful network functions.
"""

import copy
import json
import yaml
import warnings
import numpy as np

from abc import ABC, ABCMeta
from collections import defaultdict

from ..kernel.timeline import Timeline
from ..kernel.quantum_manager import KET_STATE_FORMALISM, QuantumManager

from .topology_families import TopologyFamily
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
    
    def __init__(self, config: "str | dict", family: TopologyFamily, **kwargs):
        """Build a network topology from a config file or a config dict.

        If kwargs are provided they are merged into an internal build config
        (lists extended, dicts updated, scalars overridden).

        Args:
            config (str | dict): path to a .json or .yaml/.yml file, or a config dict.
            family (TopologyFamily): composed behavior object for this topology family.
            **kwargs: additional config values to merge into the build config
                (e.g. nodes, templates, stop_time).
        """
        if isinstance(config, str):  # Note: Could widen this to PathLike later if needed.
            self.config = self.load_config(config)
        elif isinstance(config, dict):
            # If we use the same dict config 2+ times (unlikely) we shouldn't mutate it before reuse.
            self.config = copy.deepcopy(config)
        else:
            raise TypeError(
                f"config must be a file path (str) or a config dict, got {type(config).__name__}"
            )
        if kwargs:
            self.merge_overrides(self.config, kwargs)
        if ALL_NODE not in self.config or not self.config[ALL_NODE]:
            raise ValueError("Config must contain a non-empty 'nodes' list.")
        self.setup(self.config, family)

    @staticmethod
    def load_config(path: str) -> dict:
        """Load a JSON or YAML config file and return the parsed dict."""
        try:
            if path.endswith(('.yaml', '.yml')):
                with open(path) as fh:
                    return yaml.safe_load(fh)
            if path.endswith('.json'):
                with open(path) as fh:
                    return json.load(fh)
            raise ValueError(
                f"Unsupported config file format: {path}. "
                "Use .json or .yaml/.yml"
            )
        except OSError as exc:
            raise ValueError(f"Failed to read config file '{path}': {exc}") from exc
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse YAML config file '{path}': {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON config file '{path}': {exc}") from exc

    @staticmethod
    def merge_overrides(build_config: dict, extra_config: dict) -> None:
        """Merge extra config values into a build config dict in place.

        Lists are extended, dicts are updated, everything else is overridden.
        """
        LIST_KEYS = {
            'nodes': ALL_NODE, 'qconnections': ALL_Q_CONNECT,
            'cconnections': ALL_C_CONNECT, 'qchannels': ALL_Q_CHANNEL,
            'cchannels': ALL_C_CHANNEL,
        }
        for key, val in LIST_KEYS.items():
            entries = extra_config.pop(key, None)
            if entries:
                if val not in build_config:
                    build_config[val] = []
                build_config[val].extend(entries)
        templates = extra_config.pop(ALL_TEMPLATES, None)
        if templates:
            if ALL_TEMPLATES not in build_config:
                build_config[ALL_TEMPLATES] = {}
            build_config[ALL_TEMPLATES].update(templates)
        stop_time = extra_config.pop('stop_time', None)
        if stop_time is not None:
            build_config[STOP_TIME] = stop_time
        build_config.update(extra_config)

    @staticmethod
    def _validate_qconnection_dependencies(config: dict) -> None:
        """Validate that each qconnection has a matching classical path entry."""
        for q_connect in config.get(ALL_Q_CONNECT, []):
            node1 = q_connect[CONNECT_NODE_1]
            node2 = q_connect[CONNECT_NODE_2]
            has_classical_path = False

            for cc in config.get(ALL_C_CHANNEL, []):
                if ((cc[SRC] == node1 and cc[DST] == node2)
                        or (cc[SRC] == node2 and cc[DST] == node1)):
                    has_classical_path = True
                    break

            if not has_classical_path:
                for cc in config.get(ALL_C_CONNECT, []):
                    if ((cc[CONNECT_NODE_1] == node1 and cc[CONNECT_NODE_2] == node2)
                            or (cc[CONNECT_NODE_1] == node2 and cc[CONNECT_NODE_2] == node1)):
                        has_classical_path = True
                        break

            if not has_classical_path:
                raise ValueError(
                    f"qconnection between {node1} and {node2} requires a matching "
                    "classical channel or cconnection"
                )

    def setup(self, config: dict, family: TopologyFamily) -> None:
        """Execute the full build pipeline on a build config dict."""
        self.bsm_to_router_map = {}
        self.nodes: dict[str, list[Node]] = defaultdict(list)
        self.qchannels: list[QuantumChannel] = []
        self.cchannels: list[ClassicalChannel] = []
        self.templates: dict[str, dict] = {}
        self.tl: Timeline | None = None
        self.family = family

        # Prepare templates, family state, and generated qconnection artifacts.
        self.templates = config.get(ALL_TEMPLATES, {})
        self.family.configure_family(config, self.templates)
        self._add_qconnections(config)

        # Create the timeline, instantiate nodes, and wire family-specific node state.
        self.add_timeline(config)
        self.family.prepare_build_state(config, self.bsm_to_router_map)
        self.add_nodes(config)
        self.family.wire_post_nodes(self.bsm_to_router_map, self.tl)

        # Create channels, derive routing state, and attach any family protocols.
        self._add_qchannels(config)
        self._add_cchannels(config)
        self._add_cconnections(config)
        self.family.generate_forwarding_table(config, self.nodes, self.qchannels)
        self.family.attach_protocols()

    def add_nodes(self, config: dict):
        ordered_configs = self.family.order_nodes(config[ALL_NODE])
        for node_config in ordered_configs:
            node_type = node_config[TYPE]
            template  = self.templates.get(node_config.get(TEMPLATE), {})
            self.family.build_node(node_config, node_type, template,
                                   self.tl, self.nodes, self.bsm_to_router_map)

    def add_timeline(self, config: dict):
        stop_time = config.get(STOP_TIME, float('inf'))
        formalism = config.get(FORMALISM, KET_STATE_FORMALISM)
        truncation = config.get(TRUNC, 1)
        QuantumManager.set_global_manager_formalism(formalism)
        self.tl = Timeline(stop_time=stop_time, truncation=truncation)

    def _add_qchannels(self, config: dict) -> None:
        for qc in config.get(ALL_Q_CHANNEL, []):
            src_str, dst_str = qc[SRC], qc[DST]
            src_node = self.tl.get_entity_by_name(src_str)
            if src_node is not None:
                name = qc.get(NAME, f"qc-{src_str}-{dst_str}")
                qc_obj = QuantumChannel(name, self.tl, qc[ATTENUATION], qc[DISTANCE])
                qc_obj.set_ends(src_node, dst_str)
                self.qchannels.append(qc_obj)

    def _add_qconnections(self, config: dict) -> None:
        self._validate_qconnection_dependencies(config)
        for q_connect in config.get(ALL_Q_CONNECT, []):
            node1    = q_connect[CONNECT_NODE_1]
            node2    = q_connect[CONNECT_NODE_2]
            cc_delay = int(self._calc_cc_delay(config, node1, node2))
            self.family.expand_qconnection(q_connect, cc_delay, config)

    def _add_cchannels(self, config: dict) -> None:
        for cc in config.get(ALL_C_CHANNEL, []):
            self._make_classical_channel(
                cc[SRC],
                cc[DST],
                cc.get(DISTANCE, -1),
                cc.get(DELAY, -1),
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
        return float(np.mean(cc_delay) // 2)

    def _make_classical_channel(self, src_str: str, dst_str: str,
                                 distance: float, delay: int,
                                 name: str = None) -> None:
        src_obj = self.tl.get_entity_by_name(src_str)
        if src_obj is not None:
            cc_obj = ClassicalChannel(
                name or f"cc-{src_str}-{dst_str}",
                self.tl,
                distance,
                delay,
            )
            cc_obj.set_ends(src_obj, dst_str)
            self.cchannels.append(cc_obj)

    def get_timeline(self) -> "Timeline":
        if self.tl is None:
            raise RuntimeError("Timeline is not set — topology may not be fully initialized.")
        return self.tl

    def get_nodes_by_type(self, type: str) -> list[Node]:
        return self.nodes[type]

    def get_qchannels(self) -> list["QuantumChannel"]:
        return self.qchannels

    def get_cchannels(self) -> list["ClassicalChannel"]:
        return self.cchannels

    def get_nodes(self) -> dict[str, list["Node"]]:
        return self.nodes
