"""Definition of rule manager.

This module defines the rule manager, which is used by the resource manager to instantiate and control entanglement protocols.
This is achieved through rules (also defined in this module), which if met define a set of actions to take.
"""

from typing import Callable, TYPE_CHECKING, List, Tuple, Any, Dict
from ..utils import log
if TYPE_CHECKING:
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol
    from .memory_manager import MemoryInfo, MemoryManager
    from .resource_manager import ResourceManager
    from ..network_management.reservation import Reservation


ActionFunc = Callable[[List["MemoryInfo"], Dict[str, Any]],
                      Tuple["EntanglementProtocol", List["str"],
                            List[Callable[["EntanglementProtocol"], bool]]]]

ConditionFunc = Callable[["MemoryInfo", "MemoryManager", Dict[str, Any]],
                         List["MemoryInfo"]],

Arguments = Dict[str, Any]


class RuleManager:
    """Class to manage and follow installed rules.

    The RuleManager checks available rules when the state of a memory is updated.
    Rules that are met have their action executed by the rule manager.

    Attributes:
        rules (List[Rules]): List of installed rules.
        resource_manager (ResourceManager): reference to the resource manager using this rule manager.
    """

    def __init__(self):
        """Constructor for rule manager class."""

        self.rules = []
        self.resource_manager = None

    def set_resource_manager(self, resource_manager: "ResourceManager"):
        """Method to set overseeing resource manager.

        Args:
            resource_manager (ResourceManager): resource manager to attach to.
        """

        self.resource_manager = resource_manager

    def load(self, rule: "Rule") -> bool:
        """Method to load rule into ruleset.

        Tries to insert rule into internal `rules` list based on priority.

        Args:
            rule (Rule): rule to insert.

        Returns:
            bool: success of rule insertion.
        """

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
        """Method to remove expired protocol.

        Args:
            rule (Rule): rule to remove.

        Returns:
            List[EntanglementProtocol]: list of protocols created by rule (if any).
        """

        self.rules.remove(rule)
        return rule.protocols

    def get_memory_manager(self):
        return self.resource_manager.get_memory_manager()

    def send_request(self, protocol, req_dst, req_condition_func, req_args):
        log.logger.info('Rule manager send request for protocol {} to {}'.format(protocol.name, req_dst))
        return self.resource_manager.send_request(protocol, req_dst,
                                                  req_condition_func, req_args)

    def __len__(self):
        return len(self.rules)

    def __getitem__(self, item):
        return self.rules[item]


class Rule:
    """Definition of rule for the rule manager.

    Rule objects are installed on and interacted with by the rule manager.

    Attributes:
        priority (int): priority of the rule, used as a tiebreaker when conditions of multiple rules are met.
        action (Callable[[List["MemoryInfo"]], Tuple["Protocol", List["str"], List[Callable[["Protocol"], bool]]]]):
            action to take when rule condition is met.
        condition (Callable[["MemoryInfo", "MemoryManager"], List["MemoryInfo"]]): condition required by rule.
        protocols (List[Protocols]): protocols created by rule.
        rule_manager (RuleManager): reference to rule manager object where rule is installed.
        reservation (Reservation): associated reservation.
    """

    def __init__(self, priority: int, action: ActionFunc, condition: ConditionFunc,
                 action_args: Arguments, condition_args: Arguments):
        """Constructor for rule class."""

        self.priority: int = priority
        self.action: ActionFunc = action
        self.action_args: Arguments = action_args
        self.condition: ConditionFunc = condition
        self.condition_args: Arguments = condition_args
        self.protocols: List[EntanglementProtocol] = []
        self.rule_manager = None
        self.reservation = None

    def set_rule_manager(self, rule_manager: "RuleManager") -> None:
        """Method to assign rule to a rule manager.

        Args:
            rule_manager (RuleManager): manager to assign.
        """

        self.rule_manager = rule_manager

    def do(self, memories_info: List["MemoryInfo"]) -> None:
        """Method to perform rule activation and send requirements to other nodes.

        Args:
            memories_info (List[MemoryInfo]): list of memory infos for memories meeting requirements.
        """

        protocol, req_dsts, req_condition_funcs, req_args = self.action(
            memories_info, self.action_args)
        log.logger.info('Rule generates protocol {}'.format(protocol.name))

        protocol.rule = self
        self.protocols.append(protocol)
        for info in memories_info:
            info.memory.detach(info.memory.memory_array)
            info.memory.attach(protocol)
        for dst, req_func, args in zip(req_dsts, req_condition_funcs, req_args):
            self.rule_manager.send_request(protocol, dst, req_func, args)

    def is_valid(self, memory_info: "MemoryInfo") -> List["MemoryInfo"]:
        """Method to check for memories meeting condition.

        Args:
            memory_info (MemoryInfo): memory info object to test.

        Returns:
            List[memory_info]: list of memory info objects meeting requirements of rule.
        """

        manager = self.rule_manager.get_memory_manager()
        return self.condition(memory_info, manager, self.condition_args)

    def set_reservation(self, reservation: "Reservation") -> None:
        self.reservation = reservation

    def get_reservation(self) -> "Reservation":
        return self.reservation
