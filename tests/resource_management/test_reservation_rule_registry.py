from sequence.resource_management.reservation_rule_registry import (
    DEFAULT_RESERVATION_RULE_CONSTRUCTORS,
    EGRequestRule,
    EG_REQUEST,
    EPAwaitRule,
    EP_AWAIT,
    EPRequestRule,
    EP_REQUEST,
    DefaultReservationRuleGenerator,
    ReservationRuleRegistry,
)
from sequence.resource_management.rule_manager import Rule


def test_registry_can_disable_individual_rule_constructor():
    registry = ReservationRuleRegistry(DEFAULT_RESERVATION_RULE_CONSTRUCTORS)

    assert registry.get(EP_REQUEST) is EPRequestRule

    registry.disable(EP_REQUEST)

    assert registry.get(EP_REQUEST) is None
    assert registry.get(EG_REQUEST) is EGRequestRule
    assert registry.get(EP_AWAIT) is EPAwaitRule


def test_registry_can_replace_individual_rule_constructor():
    registry = ReservationRuleRegistry(DEFAULT_RESERVATION_RULE_CONSTRUCTORS)

    class CustomEPRequestRule(Rule):
        def __init__(self, *_args, **_kwargs) -> None:
            super().__init__(10, lambda *_: [], lambda *_: [], {}, {})

    registry.register(EP_REQUEST, CustomEPRequestRule)

    assert registry.get(EP_REQUEST) is CustomEPRequestRule
    assert registry.get(EG_REQUEST) is EGRequestRule


def test_default_generator_uses_registry_to_disable_rule():
    registry = ReservationRuleRegistry(DEFAULT_RESERVATION_RULE_CONSTRUCTORS)
    generator = DefaultReservationRuleGenerator(registry)

    class Owner:
        name = "node1"
        map_to_middle_node = {"node2": "middle"}

    class Reservation:
        memory_size = 1
        fidelity = 0.9
        purification_mode = "BBPSSW"

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
