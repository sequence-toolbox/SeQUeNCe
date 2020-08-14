"""Definition of rule manager.

This module defines the rule manager, which is used by the resource manager to instantiate and control entanglement protocols.
This is achieved through rules (also defined in this module), which if met define a set of actions to take.
"""

from typing import Callable, TYPE_CHECKING, List, Tuple
if TYPE_CHECKING:
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol
    from .memory_manager import MemoryInfo, MemoryManager
    from .resource_manager import ResourceManager
    from ..network_management.reservation import Reservation


class RuleManager():
    """Class to manage and follow installed rules.

    The RuleManager checks available rules when the state of a memory is updated.
    Rules that are met have their action executed by the rule manager.

    Attributes:
        rules (List[Rules]): List of installed rules.
        resource_manager (ResourceManager): reference to the resource manager using this rule manager.
    """

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

    def expire(self, rule: "Rule") -> List["EntanglementProtocol"]:
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
    """Definition of rule for the rule manager.

    Rule objects are installed on and interacted with by the rule manager.

    Attributes:
        priority (int): priority of the rule, used as a tiebreaker when conditions of multiple rules are met.
        action (Callable[[List["MemoryInfo"]], Tuple["Protocol", List["str"], List[Callable[["Protocol"], bool]]]]):
            action to take when rule condition is met.
        condition (Callable[["MemoryInfo", "MemoryManager"], List["MemoryInfo"]]): condition required by rule.
        protocols (List[Protocols]): protocols created by rule.
        rule_manager (RuleManager): reference to rule manager object where rule is installed.
    """

    def __init__(self, priority: int,
                 action: Callable[
                     [List["MemoryInfo"]], Tuple["Protocol", List["str"], List[Callable[["Protocol"], bool]]]],
                 condition: Callable[["MemoryInfo", "MemoryManager"], List["MemoryInfo"]]):
        self.priority = priority
        self.action = action
        self.condition = condition
        self.protocols = []
        self.rule_manager = None

    def set_rule_manager(self, rule_manager: "RuleManager") -> None:
        self.rule_manager = rule_manager

    def do(self, memories_info: List["MemoryInfo"]) -> None:
        protocol, req_dsts, req_condition_funcs = self.action(memories_info)
        protocol.rule = self
        self.protocols.append(protocol)
        for info in memories_info:
            info.memory.add_protocol(protocol)
        for dst, req_func in zip(req_dsts, req_condition_funcs):
            self.rule_manager.send_request(protocol, dst, req_func)

    def is_valid(self, memory_info: "MemoryInfo") -> List["MemoryInfo"]:
        manager = self.rule_manager.get_memory_manager()
        return self.condition(memory_info, manager)

    def set_reservation(self, reservation: "Reservation") -> None:
        self.reservation = reservation

    def get_reservation(self) -> "Reservation":
        return self.reservation
