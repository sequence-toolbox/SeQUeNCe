"""Default rule generation for reservation-based entanglement management.

This module defines the default generator used by the resource manager to create
entanglement generation, purification, and swapping rules for a reservation.

The default behavior matches ResourceManager.generate_load_rules, while allowing
subclasses to override parts of reservation rule creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .action_condition_set import (
    eg_rule_action_await,
    eg_rule_action_request,
    eg_rule_condition,
    ep_rule_action_await,
    ep_rule_action_request,
    ep_rule_condition_await,
    ep_rule_condition_request,
    es_rule_action_A,
    es_rule_action_B,
    es_rule_condition_A,
    es_rule_condition_B,
    es_rule_condition_B_end,
)
from .rule_manager import Rule

if TYPE_CHECKING:
    from ..network_management.reservation import Reservation
    from ..topology.node import QuantumRouter


class DefaultReservationRuleGenerator:
    """Default generator for reservation-created entanglement management rules.

    The methods in this class preserve the original rule-construction behavior
    of ResourceManager.generate_load_rules while allowing subclasses to override
    generation, purification, or swapping rule creation independently.
    """

    def create_generation_rules(
        self,
        owner: "QuantumRouter",
        path: list[str],
        reservation: "Reservation",
        memory_indices: list[int],
        index: int,
    ) -> list[Rule]:
        """Create entanglement generation rules for this node."""

        rules = []

        if index > 0:
            condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
            action_args = {
                "mid": owner.map_to_middle_node[path[index - 1]],
                "path": path,
                "index": index,
            }
            rule = Rule(10, eg_rule_action_await, eg_rule_condition, action_args, condition_args)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
            else:
                condition_args = {"memory_indices": memory_indices[reservation.memory_size:]}

            action_args = {
                "mid": owner.map_to_middle_node[path[index + 1]],
                "path": path,
                "index": index,
                "name": owner.name,
                "reservation": reservation,
            }
            rule = Rule(10, eg_rule_action_request, eg_rule_condition, action_args, condition_args)
            rules.append(rule)

        return rules

    def create_purification_rules(
        self,
        _owner: "QuantumRouter",
        path: list[str],
        reservation: "Reservation",
        memory_indices: list[int],
        index: int,
    ) -> list[Rule]:
        """Create entanglement purification rules for this node."""

        rules = []

        if index > 0:
            condition_args = {
                "memory_indices": memory_indices[:reservation.memory_size],
                "reservation": reservation,
                "purification_mode": reservation.purification_mode,
            }
            action_args = {}
            rule = Rule(10, ep_rule_action_request, ep_rule_condition_request, action_args, condition_args)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                condition_args = {
                    "memory_indices": memory_indices,
                    "fidelity": reservation.fidelity,
                    "purification_mode": reservation.purification_mode,
                }
            else:
                condition_args = {
                    "memory_indices": memory_indices[reservation.memory_size:],
                    "fidelity": reservation.fidelity,
                    "purification_mode": reservation.purification_mode,
                }

            action_args = {}
            rule = Rule(10, ep_rule_action_await, ep_rule_condition_await, action_args, condition_args)
            rules.append(rule)
        return rules

    def create_swapping_rules(
        self,
        owner: "QuantumRouter",
        path: list[str],
        reservation: "Reservation",
        memory_indices: list[int],
        index: int,
    ) -> list[Rule]:
        """Create entanglement swapping rules for this node."""

        rules = []

        if index == 0:
            condition_args = {
                "memory_indices": memory_indices,
                "target_remote": path[-1],
                "fidelity": reservation.fidelity,
            }
            action_args = {}
            rule = Rule(10, es_rule_action_B, es_rule_condition_B_end, action_args, condition_args)
            rules.append(rule)

        elif index == len(path) - 1:
            action_args = {}
            condition_args = {
                "memory_indices": memory_indices,
                "target_remote": path[0],
                "fidelity": reservation.fidelity,
            }
            rule = Rule(10, es_rule_action_B, es_rule_condition_B_end, action_args, condition_args)
            rules.append(rule)

        else:
            _path = path[:]
            while _path.index(owner.name) % 2 == 0:
                new_path = []
                for i, n in enumerate(_path):
                    if i % 2 == 0 or i == len(_path) - 1:
                        new_path.append(n)
                _path = new_path

            _index = _path.index(owner.name)
            left, right = _path[_index - 1], _path[_index + 1]

            condition_args = {
                "memory_indices": memory_indices,
                "left": left,
                "right": right,
                "fidelity": reservation.fidelity,
            }
            action_args = {}
            rule = Rule(10, es_rule_action_A, es_rule_condition_A, action_args, condition_args)
            rules.append(rule)

            action_args = {}
            rule = Rule(10, es_rule_action_B, es_rule_condition_B, action_args, condition_args)
            rules.append(rule)

        return rules

    def create_rules(
        self,
        owner: "QuantumRouter",
        path: list[str],
        reservation: "Reservation",
        memory_indices: list[int],
        index: int,
    ) -> list[Rule]:
        """Create all default rules for this reservation at this node."""

        rules = []
        rules.extend(self.create_generation_rules(owner, path, reservation, memory_indices, index))
        rules.extend(self.create_purification_rules(owner, path, reservation, memory_indices, index))
        rules.extend(self.create_swapping_rules(owner, path, reservation, memory_indices, index))
        return rules
