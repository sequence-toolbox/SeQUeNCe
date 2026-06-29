from numpy import random
from sequence.components.memory import Memory
from sequence.kernel.timeline import Timeline
from sequence.resource_management.memory_manager import MemoryInfo
from sequence.resource_management.rule_manager import RuleManager, Rule

random.seed(1)


def test_Rule_do():
    class FakeRuleManager(RuleManager):
        def __init__(self):
            RuleManager.__init__(self)
            self.log = []

        def send_request(self, protocol, req_dst, req_condition, req_args):
            self.log.append((protocol.name, req_dst, req_condition, req_args))

    class FakeProtocol():
        def __init__(self, name):
            self.name = name
            self.rule = None
            self.memories = []

    def fake_action(memories_info, args):
        assert args["exist"]
        if len(memories_info) == 1:
            return FakeProtocol("protocol1"), ["req_dst1"], ["req_condition1"], [{}]
        else:
            return FakeProtocol("protocol2"), [None], [None], [{}]

    tl = Timeline()
    rule_manager = FakeRuleManager()
    action_args = {"exist": True}
    rule = Rule(1, fake_action, None, action_args, None)
    rule.set_rule_manager(rule_manager)
    assert rule.priority == 1 and len(rule.protocols) == 0
    memory = Memory("mem", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=-1, wavelength=500)
    memories_info = [MemoryInfo(memory, 0)]
    assert len(memory._observers) == 0
    rule.do(memories_info)
    assert len(rule.protocols) == 1 and rule.protocols[0].name == "protocol1"
    assert len(rule_manager.log) == 1
    assert rule_manager.log[0] == (
        "protocol1", "req_dst1", "req_condition1", {})
    assert rule.protocols[0].rule == rule
    assert len(memory._observers) == 1
    mem1 = Memory("1", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=-1, wavelength=500)
    mem2 = Memory("2", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=-1, wavelength=500)
    memories_info = [MemoryInfo(mem1, 0), MemoryInfo(mem2, 1)]
    rule.do(memories_info)
    assert len(rule.protocols) == 2 and rule.protocols[1].name == "protocol2"
    assert len(rule_manager.log) == 2 and rule_manager.log[1] == (
        "protocol2", None, None, {})
    assert rule.protocols[1].rule == rule
    assert len(mem1._observers) == len(mem2._observers) == 1


def test_Rule_is_valid():
    class FakeRuleManager():
        def __init__(self):
            pass

        def get_memory_manager(self):
            return 0.5

    def fake_condition(val1, val2, args):
        assert args["exist"]
        return val1 < 0.5

    condition_args = {"exist": True}
    rule = Rule(1, None, fake_condition, None, condition_args)
    rule.set_rule_manager(FakeRuleManager())
    for _ in range(100):
        val1 = random.random()
        assert rule.is_valid(val1) == (val1 < 0.5)


def test_RuleManager_load():
    rule_manager = RuleManager()
    for _ in range(100):
        priority = random.randint(20)
        rule = Rule(priority, None, None, None, None)
        rule_manager.load(rule)

    for i in range(1, len(rule_manager)):
        assert rule_manager[i].priority >= rule_manager[i - 1].priority
        assert id(rule_manager[i].rule_manager) == id(rule_manager)


def test_RuleManager_expire():
    ruleset = RuleManager()
    rule = Rule(1, None, None, None, None)
    rule.protocols.append("protocol")
    assert ruleset.load(rule) and len(ruleset) == 1
    protocol = ruleset.expire(rule)
    assert len(ruleset) == 0
    assert protocol == ["protocol"]
