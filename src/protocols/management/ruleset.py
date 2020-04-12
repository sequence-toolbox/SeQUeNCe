from typing import Callable, TYPE_CHECKING, List

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ..protocol import Protocol
    from .memory import MemoryManager


class Ruleset():
    def __init__(self):
        self.rules = []

    def load(self, rule: "Rule") -> bool:
        # binary search for inserting rule
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

    def __len__(self):
        return len(self.rules)

    def __getitem__(self, item):
        return self.rules[item]


class Rule():
    def __init__(self, priority: int, action: Callable[[List["Memory"]], "Protocol"],
                 condition: Callable[["Memory", "MemoryManager"], List["Memory"]]):
        self.priority = priority
        self.action = action
        self.is_valid = condition
        self.protocols = []

    def do(self, memories: List["Memory"]) -> None:
        protocol = self.action(memories)
        self.protocols.append(protocol)

    def is_valid(self, memory: "Memory", manager: "MemoryManager") -> List["Memory"]:
        return self.is_valid(memory, manager)
