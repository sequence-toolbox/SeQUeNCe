from typing import Callable, TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ..protocol import Protocol
    from .memory_manager import MemoryInfo
    from .manager import ResourceManager


class RuleManager():
    def __init__(self):
        self.rules = []
        self.resource_manager = None

    def set_resource_manager(self, resource_manager: "ResourceManager"):
        self.resource_manager = resource_manager

    def load(self, rule: "Rule") -> bool:
        # binary search for inserting rule
        rule.set_rule_manager(self)
        left, right = 0, len(self.rules) - 1
        while left <= right:
            mid = (left + right) // 2
            if self.rules[mid].priority < rule.priority:
                left = mid + 1
            else:
                right = mid - 1
        self.rules.insert(left, rule)
        return True

    def expire(self, rule: "Rule") -> List["Protocol"]:
        """
        expire function return protocols created by expired rule
        """
        self.rules.remove(rule)
        return rule.protocols

    def get_memory_manager(self):
        return self.resource_manager.get_memory_manager()

    def send_request(self, protocol, req_dst, req_condition_func):
        return self.resource_manager.send_request(protocol, req_dst, req_condition_func)

    def __len__(self):
        return len(self.rules)

    def __getitem__(self, item):
        return self.rules[item]


class Rule():
    def __init__(self, priority: int,
                 action: Callable[[List["Memory"]], Tuple["Protocol", "str", Callable[["Protocol"], None]]],
                 condition: Callable[["MemoryInfo"], List["Memory"]]):
        self.priority = priority
        self.action = action
        self.condition = condition
        self.protocols = []
        self.rule_manager = None

    def set_rule_manager(self, rule_manager: "RuleManager") -> None:
        self.rule_manager = rule_manager

    def do(self, memories: List["Memory"]) -> None:
        protocol, req_dst, req_condition_func = self.action(memories)
        self.protocols.append(protocol)
        self.rule_manager.send_request(protocol, req_dst, req_condition_func)

    def is_valid(self, memory_info: "MemoryInfo") -> List["Memory"]:
        manager = self.rule_manager.get_memory_manager()
        return self.condition(memory_info, manager)
