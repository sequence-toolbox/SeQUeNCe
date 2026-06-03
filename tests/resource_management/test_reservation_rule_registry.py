from sequence.resource_management.reservation_rule_registry import (
    DEFAULT_RESERVATION_RULE_CONSTRUCTORS,
    EGRequestRule,
    EG_REQUEST,
    EPAwaitRule,
    EP_AWAIT,
    EPRequestRule,
    EP_REQUEST,
    ReservationRuleGenerator,
    ReservationRuleRegistry,
)
from sequence.resource_management.rule_manager import Rule


class Owner:
    name = "node1"
    map_to_middle_node = {"node2": "middle"}


class Reservation:
    memory_size = 1
    fidelity = 0.9
    purification_mode = "BBPSSW"


def test_registry_can_disable_individual_rule_constructor():
    registry = ReservationRuleRegistry(DEFAULT_RESERVATION_RULE_CONSTRUCTORS)

    assert registry.get(EP_REQUEST) is EPRequestRule

    registry.disable(EP_REQUEST)

    assert registry.get(EP_REQUEST) is None
    assert registry.get(EG_REQUEST) is EGRequestRule
    assert registry.get(EP_AWAIT) is EPAwaitRule


def test_registry_can_replace_individual_rule_constructor():
    registry = ReservationRuleRegistry(DEFAULT_RESERVATION_RULE_CONSTRUCTORS)

    class CustomEPRequestRule(EPRequestRule):
        pass

    registry.register(EP_REQUEST, CustomEPRequestRule)

    assert registry.get(EP_REQUEST) is CustomEPRequestRule
    assert registry.get(EG_REQUEST) is EGRequestRule


def test_generator_uses_registered_replacement_rule():
    generator = ReservationRuleGenerator()

    class CustomEGRequestRule(EGRequestRule):
        pass

    generator.registry.register(EG_REQUEST, CustomEGRequestRule)

    rules = generator.create_rules(
        Owner(),
        ["node1", "node2"],
        Reservation(),
        [0],
        0,
    )

    assert all(isinstance(rule, Rule) for rule in rules)
    assert any(isinstance(rule, CustomEGRequestRule) for rule in rules)
    assert not any(type(rule) is EGRequestRule for rule in rules)


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
    assert any(isinstance(rule, EGRequestRule) for rule in rules)
    assert any(isinstance(rule, EPAwaitRule) for rule in rules)

    registry.disable(EP_AWAIT)

    rules = generator.create_rules(
        Owner(),
        ["node1", "node2"],
        Reservation(),
        [0],
        0,
    )

    assert any(isinstance(rule, EGRequestRule) for rule in rules)
    assert not any(isinstance(rule, EPAwaitRule) for rule in rules)
