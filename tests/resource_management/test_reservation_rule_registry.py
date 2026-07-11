import pytest

from sequence.resource_management.action_condition_set import (
    eg_rule_action_request,
    ep_rule_action_await,
    es_rule_action_A,
)
from sequence.resource_management.reservation_rule_registry import (
    DEFAULT_RESERVATION_RULE_SPECS,
    EG_AWAIT,
    EG_REQUEST,
    EP_AWAIT,
    EP_REQUEST,
    ES_A,
    ES_B,
    ES_B_END,
    ReservationRuleContext,
    ReservationRuleGenerator,
    ReservationRuleRegistry,
)
from sequence.resource_management.rule_manager import Rule


class Owner:
    name = "node1"
    map_to_middle_node = {"node0": "middle_left", "node2": "middle_right"}
    swapping_success_prob = 0.75
    swapping_degradation = 0.95


class Reservation:
    memory_size = 1
    fidelity = 0.9
    purification_mode = "BBPSSW"


def _custom_rule_builder(context: ReservationRuleContext) -> Rule:
    return Rule(10, eg_rule_action_request, lambda *_args: [], {"custom": context.index}, {})


def test_registry_can_disable_individual_rule_builder():
    registry = ReservationRuleRegistry()

    assert registry.get(EP_REQUEST) is not None

    registry.disable(EP_REQUEST)

    assert registry.get(EP_REQUEST) is None
    assert registry.get(EG_REQUEST) is not None
    assert registry.get(EP_AWAIT) is not None


def test_registry_can_replace_individual_rule_builder():
    registry = ReservationRuleRegistry()

    registry.replace(EP_REQUEST, _custom_rule_builder)

    assert registry.get(EP_REQUEST) is _custom_rule_builder
    assert registry.get(EG_REQUEST) is not _custom_rule_builder


def test_registry_rejects_unknown_rule_name():
    registry = ReservationRuleRegistry()

    with pytest.raises(ValueError):
        registry.replace("custom_phase", _custom_rule_builder)


def test_registry_rejects_builder_with_wrong_signature():
    registry = ReservationRuleRegistry()

    def bad_builder():
        return Rule(10, eg_rule_action_request, lambda *_args: [], {}, {})

    with pytest.raises(TypeError):
        registry.replace(EP_REQUEST, bad_builder)


def test_generator_uses_replacement_builder():
    generator = ReservationRuleGenerator()
    generator.registry.replace(EG_REQUEST, _custom_rule_builder)

    rules = generator.create_rules(
        Owner(),
        ["node1", "node2"],
        Reservation(),
        [0],
        0,
    )

    assert all(isinstance(rule, Rule) for rule in rules)
    assert any(rule.action_args == {"custom": 0} for rule in rules)
    assert not any(rule.action is eg_rule_action_request and "custom" not in rule.action_args for rule in rules)


def test_generator_uses_registry_to_disable_rule():
    generator = ReservationRuleGenerator()
    registry = generator.registry

    rules = generator.create_rules(
        Owner(),
        ["node1", "node2"],
        Reservation(),
        [0],
        0,
    )

    assert all(isinstance(rule, Rule) for rule in rules)
    assert any(rule.action is eg_rule_action_request for rule in rules)
    assert any(rule.action is ep_rule_action_await for rule in rules)

    registry.disable(EP_AWAIT)

    rules = generator.create_rules(
        Owner(),
        ["node1", "node2"],
        Reservation(),
        [0],
        0,
    )

    assert any(rule.action is eg_rule_action_request for rule in rules)
    assert not any(rule.action is ep_rule_action_await for rule in rules)


def test_generator_uses_static_default_rule_spec_order():
    generator = ReservationRuleGenerator()

    def marker_builder(name):
        def build(_context: ReservationRuleContext) -> Rule:
            return Rule(10, eg_rule_action_request, lambda *_args: [], {"slot": name}, {})

        return build

    for rule_name in (EG_AWAIT, EG_REQUEST, EP_REQUEST, EP_AWAIT, ES_B_END, ES_A, ES_B):
        generator.registry.replace(rule_name, marker_builder(rule_name))

    rules = generator.create_rules(
        Owner(),
        ["node0", "node1", "node2"],
        Reservation(),
        [0, 1],
        1,
    )

    context = ReservationRuleContext(Owner(), ["node0", "node1", "node2"], Reservation(), [0, 1], 1)
    expected_names = [spec.name for spec in DEFAULT_RESERVATION_RULE_SPECS if spec.predicate(context)]
    actual_names = [rule.action_args["slot"] for rule in rules]

    assert actual_names == expected_names


def test_default_es_a_rule_preserves_swapping_action_args():
    generator = ReservationRuleGenerator()

    rules = generator.create_rules(
        Owner(),
        ["node0", "node1", "node2"],
        Reservation(),
        [0, 1],
        1,
    )

    es_a_rules = [rule for rule in rules if rule.action is es_rule_action_A]
    assert len(es_a_rules) == 1
    assert es_a_rules[0].action_args == {
        "swapping_success_prob": Owner.swapping_success_prob,
        "swapping_degradation": Owner.swapping_degradation,
    }
    assert es_a_rules[0].condition_args["left"] == "node0"
    assert es_a_rules[0].condition_args["right"] == "node2"
