from numpy import random
from sequence.protocols.management.ruleset import *

random.seed(1)


def test_Rule_do():
    def fake_action(args):
        return "fake_protocol with args=" + str(args)

    rule = Rule(1, fake_action, None)
    assert rule.priority == 1 and len(rule.protocols) == 0
    rule.do("memories")
    print(rule.protocols)
    assert rule.protocols[0] == "fake_protocol with args=memories"


def test_Rule_is_valid():
    def fake_condition(val1, val2):
        return val1 < val2

    rule = Rule(1, None, fake_condition)
    for _ in range(100):
        val1, val2 = random.random(), random.random()
        assert rule.is_valid(val1, val2) == (val1 < val2)


def test_Ruleset_load():
    ruleset = Ruleset()
    for _ in range(100):
        priority = random.randint(20)
        rule = Rule(priority, None, None)
        ruleset.load(rule)

    for i in range(1, len(ruleset)):
        assert ruleset[i].priority >= ruleset[i - 1].priority


def test_Ruleset_expire():
    ruleset = Ruleset()
    rule = Rule(1, None, None)
    rule.protocols.append("protocol")
    assert ruleset.load(rule) and len(ruleset) == 1
    protocol = ruleset.expire(rule)
    assert len(ruleset) == 0
    assert protocol == ["protocol"]
