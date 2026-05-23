"""Registry utilities for reservation-generated resource-management rules.

This module defines reservation-specific Rule subclasses and a registry that
maps reservation rule names to Rule constructors. The default resource-management
rule generator uses this registry to construct the built-in rules, while users
may replace or disable individual rules without subclassing the generator.
"""

from typing import Final

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

ReservationRuleConstructor = type[Rule]


class EGAwaitRule(Rule):
    """Entanglement-generation await rule for non-left-end nodes."""

    def __init__(self, owner, path, reservation, memory_indices, index) -> None:
        condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
        action_args = {
            "mid": owner.map_to_middle_node[path[index - 1]],
            "path": path,
            "index": index,
        }
        super().__init__(10, eg_rule_action_await, eg_rule_condition, action_args, condition_args)


class EGRequestRule(Rule):
    """Entanglement-generation request rule for non-right-end nodes."""

    def __init__(self, owner, path, reservation, memory_indices, index) -> None:
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
        super().__init__(10, eg_rule_action_request, eg_rule_condition, action_args, condition_args)


class EPRequestRule(Rule):
    """Entanglement-purification request rule."""

    def __init__(self, _owner, _path, reservation, memory_indices, _index) -> None:
        condition_args = {
            "memory_indices": memory_indices[:reservation.memory_size],
            "reservation": reservation,
            "purification_mode": reservation.purification_mode,
        }
        super().__init__(10, ep_rule_action_request, ep_rule_condition_request, {}, condition_args)


class EPAwaitRule(Rule):
    """Entanglement-purification await rule."""

    def __init__(self, _owner, path, reservation, memory_indices, index) -> None:
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

        super().__init__(10, ep_rule_action_await, ep_rule_condition_await, {}, condition_args)


class ESBEndRule(Rule):
    """Endpoint entanglement-swapping B rule."""

    def __init__(self, _owner, path, reservation, memory_indices, index) -> None:
        if index == 0:
            target_remote = path[-1]
        else:
            target_remote = path[0]

        condition_args = {
            "memory_indices": memory_indices,
            "target_remote": target_remote,
            "fidelity": reservation.fidelity,
        }
        super().__init__(10, es_rule_action_B, es_rule_condition_B_end, {}, condition_args)


def _get_swapping_neighbors(owner_name: str, path: list[str]) -> tuple[str, str]:
    """Return the left and right neighbors used for middle-node swapping rules."""
    reduced_path = path[:]
    while reduced_path.index(owner_name) % 2 == 0:
        new_path = []
        for i, node_name in enumerate(reduced_path):
            if i % 2 == 0 or i == len(reduced_path) - 1:
                new_path.append(node_name)
        reduced_path = new_path

    reduced_index = reduced_path.index(owner_name)
    return reduced_path[reduced_index - 1], reduced_path[reduced_index + 1]


class ESARule(Rule):
    """Middle-node entanglement-swapping A rule."""

    def __init__(self, owner, path, reservation, memory_indices, _index) -> None:
        left, right = _get_swapping_neighbors(owner.name, path)
        condition_args = {
            "memory_indices": memory_indices,
            "left": left,
            "right": right,
            "fidelity": reservation.fidelity,
        }
        super().__init__(10, es_rule_action_A, es_rule_condition_A, {}, condition_args)


class ESBRule(Rule):
    """Middle-node entanglement-swapping B rule."""

    def __init__(self, owner, path, reservation, memory_indices, _index) -> None:
        left, right = _get_swapping_neighbors(owner.name, path)
        condition_args = {
            "memory_indices": memory_indices,
            "left": left,
            "right": right,
            "fidelity": reservation.fidelity,
        }
        super().__init__(10, es_rule_action_B, es_rule_condition_B, {}, condition_args)


DEFAULT_RESERVATION_RULE_CONSTRUCTORS: Final[dict[str, ReservationRuleConstructor]] = {
    EG_AWAIT: EGAwaitRule,
    EG_REQUEST: EGRequestRule,
    EP_REQUEST: EPRequestRule,
    EP_AWAIT: EPAwaitRule,
    ES_B_END: ESBEndRule,
    ES_A: ESARule,
    ES_B: ESBRule,
}

DEFAULT_RESERVATION_RULE_ORDER: Final[tuple[str, ...]] = (
    EG_AWAIT,
    EG_REQUEST,
    EP_REQUEST,
    EP_AWAIT,
    ES_B_END,
    ES_A,
    ES_B,
)


class ReservationRuleRegistry:
    """Registry for reservation Rule constructors."""

    def __init__(self, constructors: dict[str, ReservationRuleConstructor] | None = None) -> None:
        self._constructors: dict[str, ReservationRuleConstructor] = {}
        if constructors is not None:
            for name, constructor in constructors.items():
                self.register(name, constructor)

    def register(self, name: str, constructor: ReservationRuleConstructor) -> None:
        """Register or replace a reservation Rule constructor."""
        self._validate_name(name)
        if not issubclass(constructor, Rule):
            msg = "Reservation rule constructors must be Rule subclasses"
            raise TypeError(msg)
        self._constructors[name] = constructor

    def disable(self, name: str) -> None:
        """Disable a reservation Rule constructor."""
        self._validate_name(name)
        self._constructors.pop(name, None)

    def get(self, name: str) -> ReservationRuleConstructor | None:
        """Return the constructor registered for a rule name, if any."""
        self._validate_name(name)
        return self._constructors.get(name)

    def build(self, name: str, *args, **kwargs) -> Rule | None:
        """Build a rule by name.

        Returns None when the rule is disabled.
        """
        constructor = self.get(name)
        if constructor is None:
            return None
        return constructor(*args, **kwargs)

    def copy(self) -> "ReservationRuleRegistry":
        """Return a shallow copy of this registry."""
        return ReservationRuleRegistry(self._constructors.copy())

    @staticmethod
    def _validate_name(name: str) -> None:
        if name not in RESERVATION_RULE_NAMES:
            msg = f"Unknown reservation rule name: {name}"
            raise ValueError(msg)


class DefaultReservationRuleGenerator:
    """Default generator for reservation-based resource-management rules."""

    def __init__(self, registry: ReservationRuleRegistry | None = None) -> None:
        if registry is None:
            registry = ReservationRuleRegistry(DEFAULT_RESERVATION_RULE_CONSTRUCTORS)
        self.registry = registry

    def create_rules(self, owner, path, reservation, memory_indices, index) -> list[Rule]:
        """Create reservation rules using the configured rule registry."""
        rules: list[Rule] = []

        if index > 0:
            rule = self.registry.build(EG_AWAIT, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)

        if index < len(path) - 1:
            rule = self.registry.build(EG_REQUEST, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)

        if index > 0:
            rule = self.registry.build(EP_REQUEST, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)

        if index < len(path) - 1:
            rule = self.registry.build(EP_AWAIT, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)

        if index == 0 or index == len(path) - 1:
            rule = self.registry.build(ES_B_END, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)
        else:
            rule = self.registry.build(ES_A, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)

            rule = self.registry.build(ES_B, owner, path, reservation, memory_indices, index)
            if rule is not None:
                rules.append(rule)

        return rules
