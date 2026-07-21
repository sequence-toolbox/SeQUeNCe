"""Utilities for building reservation-generated resource-management rules.

This module defines the fixed reservation rule slots used by the default
reservation rule generator.  Users may replace or disable the builders for
these existing slots, but the reservation rule order and creation predicates
remain static.
"""

from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
from typing import TYPE_CHECKING, Final
from collections.abc import Callable, Iterable

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


EG_AWAIT: Final[str] = "eg_await"
EG_REQUEST: Final[str] = "eg_request"
EP_REQUEST: Final[str] = "ep_request"
EP_AWAIT: Final[str] = "ep_await"
ES_B_END: Final[str] = "es_b_end"
ES_A: Final[str] = "es_a"
ES_B: Final[str] = "es_b"

RESERVATION_RULE_NAMES: Final[tuple[str, ...]] = (
    EG_AWAIT,
    EG_REQUEST,
    EP_REQUEST,
    EP_AWAIT,
    ES_B_END,
    ES_A,
    ES_B,
)


@dataclass(frozen=True)
class ReservationRuleContext:
    """Inputs needed to build reservation-generated resource-management rules."""

    owner: QuantumRouter
    path: list[str]
    reservation: Reservation
    memory_indices: list[int]
    index: int
    priority: int = 10


ReservationRulePredicate = Callable[[ReservationRuleContext], bool]
ReservationRuleBuilder = Callable[[ReservationRuleContext], Rule]


@dataclass(frozen=True)
class ReservationRuleSpec:
    """Static specification for one built-in reservation rule slot."""

    name: str
    predicate: ReservationRulePredicate
    builder: ReservationRuleBuilder


def _applies_eg_await(context: ReservationRuleContext) -> bool:
    return context.index > 0


def _applies_eg_request(context: ReservationRuleContext) -> bool:
    return context.index < len(context.path) - 1


def _applies_ep_request(context: ReservationRuleContext) -> bool:
    return context.index > 0


def _applies_ep_await(context: ReservationRuleContext) -> bool:
    return context.index < len(context.path) - 1


def _applies_es_b_end(context: ReservationRuleContext) -> bool:
    return context.index == 0 or context.index == len(context.path) - 1


def _applies_es_middle(context: ReservationRuleContext) -> bool:
    return 0 < context.index < len(context.path) - 1


def _build_eg_await_rule(context: ReservationRuleContext) -> Rule:
    condition_args = {"memory_indices": context.memory_indices[:context.reservation.memory_size]}
    action_args = {
        "mid": context.owner.map_to_middle_node[context.path[context.index - 1]],
        "path": context.path,
        "index": context.index,
    }
    return Rule(context.priority, eg_rule_action_await, eg_rule_condition, action_args, condition_args)


def _build_eg_request_rule(context: ReservationRuleContext) -> Rule:
    if context.index == 0:
        condition_args = {"memory_indices": context.memory_indices[:context.reservation.memory_size]}
    else:
        condition_args = {"memory_indices": context.memory_indices[context.reservation.memory_size:]}

    action_args = {
        "mid": context.owner.map_to_middle_node[context.path[context.index + 1]],
        "path": context.path,
        "index": context.index,
        "name": context.owner.name,
        "reservation": context.reservation,
    }
    return Rule(context.priority, eg_rule_action_request, eg_rule_condition, action_args, condition_args)


def _build_ep_request_rule(context: ReservationRuleContext) -> Rule:
    condition_args = {
        "memory_indices": context.memory_indices[:context.reservation.memory_size],
        "reservation": context.reservation,
        "purification_mode": context.reservation.purification_mode,
    }
    return Rule(context.priority, ep_rule_action_request, ep_rule_condition_request, {}, condition_args)


def _build_ep_await_rule(context: ReservationRuleContext) -> Rule:
    if context.index == 0:
        condition_args = {
            "memory_indices": context.memory_indices,
            "fidelity": context.reservation.fidelity,
            "purification_mode": context.reservation.purification_mode,
        }
    else:
        condition_args = {
            "memory_indices": context.memory_indices[context.reservation.memory_size:],
            "fidelity": context.reservation.fidelity,
            "purification_mode": context.reservation.purification_mode,
        }

    return Rule(context.priority, ep_rule_action_await, ep_rule_condition_await, {}, condition_args)


def _build_es_b_end_rule(context: ReservationRuleContext) -> Rule:
    if context.index == 0:
        target_remote = context.path[-1]
    else:
        target_remote = context.path[0]

    condition_args = {
        "memory_indices": context.memory_indices,
        "target_remote": target_remote,
        "fidelity": context.reservation.fidelity,
    }
    return Rule(context.priority, es_rule_action_B, es_rule_condition_B_end, {}, condition_args)


def _get_swapping_neighbors(owner_name: str, path: list[str]) -> tuple[str, str]:
    """Return the neighbors used by middle-node swapping rules.

    SeQUeNCe creates swapping rules by repeatedly reducing the path to the
    nodes that remain after each swapping layer. If the current node is at an
    even index in the reduced path, that layer is skipped and the path is
    reduced again. Once the current node is at an odd index, its immediate
    reduced-path neighbors are the left and right entanglement-swapping
    partners.
    """
    reduced_path = path[:]
    while reduced_path.index(owner_name) % 2 == 0:
        new_path = []
        for i, node_name in enumerate(reduced_path):
            if i % 2 == 0 or i == len(reduced_path) - 1:
                new_path.append(node_name)
        reduced_path = new_path

    reduced_index = reduced_path.index(owner_name)
    return reduced_path[reduced_index - 1], reduced_path[reduced_index + 1]


def _build_es_a_rule(context: ReservationRuleContext) -> Rule:
    left, right = _get_swapping_neighbors(context.owner.name, context.path)
    condition_args = {
        "memory_indices": context.memory_indices,
        "left": left,
        "right": right,
        "fidelity": context.reservation.fidelity,
    }
    action_args = {
        "swapping_success_prob": context.owner.swapping_success_prob,
        "swapping_degradation": context.owner.swapping_degradation,
    }
    return Rule(context.priority, es_rule_action_A, es_rule_condition_A, action_args, condition_args)


def _build_es_b_rule(context: ReservationRuleContext) -> Rule:
    left, right = _get_swapping_neighbors(context.owner.name, context.path)
    condition_args = {
        "memory_indices": context.memory_indices,
        "left": left,
        "right": right,
        "fidelity": context.reservation.fidelity,
    }
    return Rule(context.priority, es_rule_action_B, es_rule_condition_B, {}, condition_args)


DEFAULT_RESERVATION_RULE_SPECS: Final[tuple[ReservationRuleSpec, ...]] = (
    ReservationRuleSpec(EG_AWAIT, _applies_eg_await, _build_eg_await_rule),
    ReservationRuleSpec(EG_REQUEST, _applies_eg_request, _build_eg_request_rule),
    ReservationRuleSpec(EP_REQUEST, _applies_ep_request, _build_ep_request_rule),
    ReservationRuleSpec(EP_AWAIT, _applies_ep_await, _build_ep_await_rule),
    ReservationRuleSpec(ES_B_END, _applies_es_b_end, _build_es_b_end_rule),
    ReservationRuleSpec(ES_A, _applies_es_middle, _build_es_a_rule),
    ReservationRuleSpec(ES_B, _applies_es_middle, _build_es_b_rule),
)


class ReservationRuleRegistry:
    """Registry for replacing or disabling existing reservation rule builders."""

    def __init__(self, specs: Iterable[ReservationRuleSpec] | None = None) -> None:
        if specs is None:
            specs = DEFAULT_RESERVATION_RULE_SPECS
        self._builders: dict[str, ReservationRuleBuilder] = {}
        for spec in specs:
            self._validate_name(spec.name)
            self._validate_builder(spec.builder)
            if spec.name in self._builders:
                msg = f"Duplicate reservation rule name: {spec.name}"
                raise ValueError(msg)
            self._builders[spec.name] = spec.builder

    def replace(self, name: str, builder: ReservationRuleBuilder) -> None:
        """Replace the builder for an existing reservation rule slot."""
        self._validate_name(name)
        self._validate_builder(builder)
        self._builders[name] = builder

    def disable(self, name: str) -> None:
        """Disable an existing reservation rule slot."""
        self._validate_name(name)
        self._builders.pop(name, None)

    def get(self, name: str) -> ReservationRuleBuilder | None:
        """Return the builder for a rule slot, or None if it is disabled."""
        self._validate_name(name)
        return self._builders.get(name)

    def build(self, name: str, context: ReservationRuleContext) -> Rule | None:
        """Build the named rule for the supplied context.

        Returns None when the rule slot is disabled.
        """
        builder = self.get(name)
        if builder is None:
            return None

        rule = builder(context)
        if not isinstance(rule, Rule):
            msg = f"Reservation rule builder for {name!r} must return a Rule"
            raise TypeError(msg)
        return rule

    @staticmethod
    def _validate_name(name: str) -> None:
        if name not in RESERVATION_RULE_NAMES:
            msg = f"Unknown reservation rule name: {name}"
            raise ValueError(msg)

    @staticmethod
    def _validate_builder(builder: ReservationRuleBuilder) -> None:
        if not callable(builder):
            msg = "Reservation rule builders must be callable"
            raise TypeError(msg)

        try:
            signature(builder).bind(object())
        except (TypeError, ValueError) as exc:
            msg = "Reservation rule builders must accept a ReservationRuleContext argument"
            raise TypeError(msg) from exc


class ReservationRuleGenerator:
    """Rule generator for reservation-based resource-management rules."""

    def __init__(self) -> None:
        self.registry = ReservationRuleRegistry()

    def create_rules(
        self,
        owner: "QuantumRouter",
        path: list[str],
        reservation: "Reservation",
        memory_indices: list[int],
        index: int,
        priority: int = 10,
    ) -> list[Rule]:
        """Create reservation rules in SeQUeNCe's static rule-slot order.

        Args:
            owner: Router whose resource manager will load the generated rules.
            path: Reservation path from initiator to responder.
            reservation: Reservation used to generate the rules.
            memory_indices: Local memory indices assigned to the reservation.
            index: Position of ``owner`` in ``path``.
            priority: Priority assigned to generated rules.

        Returns:
            Reservation-generated rules whose static predicates apply at this node.
        """
        context = ReservationRuleContext(owner, path, reservation, memory_indices, index, priority)
        rules: list[Rule] = []

        for spec in DEFAULT_RESERVATION_RULE_SPECS:
            if spec.predicate(context):
                rule = self.registry.build(spec.name, context)
                if rule is not None:
                    rules.append(rule)

        return rules
