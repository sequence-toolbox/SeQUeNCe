"""Definition of rule manager.

This module defines the rule manager, which is used by the resource manager to instantiate and control entanglement protocols.
This is achieved through rules (also defined in this module), which if met define a set of actions to take.
"""

from typing import Callable, TYPE_CHECKING, Any

from ..utils import log

if TYPE_CHECKING:
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol
    from .memory_manager import MemoryInfo
    from .resource_manager import ResourceManager
    from ..network_management.reservation import Reservation

ActionFunc = Callable[[list["MemoryInfo"], dict[str, Any]], 
                      tuple["EntanglementProtocol", list["str"], list[Callable[["EntanglementProtocol"], bool]]]]

ConditionFunc = Callable[["MemoryInfo", "MemoryManager", dict[str, Any]], list["MemoryInfo"]]

Arguments = dict[str, Any]


class RuleManager:
    """Class to manage and follow installed rules.

    The RuleManager checks available rules when the state of a memories is updated.
    Rules that are met have their action executed by the rule manager.

    Attributes:
        rules (list[Rules]): list of installed rules.
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

    def expire(self, rule: "Rule") -> list["EntanglementProtocol"]:
        """Method to remove expired protocol.

        Args:
            rule (Rule): rule to remove.

        Returns:
            list[EntanglementProtocol]: list of protocols created by rule (if any).
                Note that when a protocol finishes, it will be removed from rule.protocols.
        """
        if rule in self.rules:
            self.rules.remove(rule)
        else:
            log.logger.info(f'{self.resource_manager.owner} rule not exist: {rule}')
        return rule.protocols
        

    def get_memory_manager(self):
        return self.resource_manager.get_memory_manager()

    def send_request(self, protocol, req_dst, req_condition_func, req_args):
        log.logger.info('{} Rule Manager send request for protocol {} to {}'.format(self.resource_manager.owner, protocol.name, req_dst))
        return self.resource_manager.send_request(protocol, req_dst, req_condition_func, req_args)

    def __len__(self):
        return len(self.rules)

    def __getitem__(self, item):
        return self.rules[item]
    
    def __str__(self) -> str:
        if self.resource_manager:
            return f'{self.resource_manager.owner.name} Rule Manager'
        else:
            return 'Rule Manager'


class Rule:
    """Definition of rule for the rule manager.

    Rule objects are installed on and interacted with by the rule manager.

    Attributes:
        priority (int): priority of the rule, used as a tiebreaker when conditions of multiple rules are met.
        action (Callable[[list["MemoryInfo"]], tuple["Protocol", list["str"], list[Callable[["Protocol"], bool]]]]):
            action to take when rule condition is met.
        condition (Callable[["MemoryInfo", "MemoryManager"], list["MemoryInfo"]]): condition required by rule.
        protocols (list[Protocols]): protocols created by rule.
        rule_manager (RuleManager): reference to rule manager object where rule is installed.
        reservation (Reservation): associated reservation.
    """

    def __init__(self, priority: int, action: ActionFunc, condition: ConditionFunc, action_args: Arguments, condition_args: Arguments):
        """Constructor for rule class."""

        self.priority: int = priority
        self.action: ActionFunc = action
        self.action_args: Arguments = action_args
        self.condition: ConditionFunc = condition
        self.condition_args: Arguments = condition_args
        self.protocols: list[EntanglementProtocol] = []
        self.rule_manager = None
        self.reservation = None

    def __str__(self):
        action_name_list = str(self.action).split(' ')
        action_name = action_name_list[1] if len(action_name_list) >= 2 else action_name_list[0]  # in case action_name = ['None']
        condition_name_list = str(self.condition).split(' ')
        condition_name = condition_name_list[1] if len(condition_name_list) >= 2 else condition_name_list[0]
        return "|action={}, args={}; condition={}; args={}|".format(action_name, self.action_args, condition_name, self.condition_args)

    def set_rule_manager(self, rule_manager: "RuleManager") -> None:
        """Method to assign rule to a rule manager.

        Args:
            rule_manager (RuleManager): manager to assign.
        """

        self.rule_manager = rule_manager

    def do(self, memories_info: list["MemoryInfo"]) -> None:
        """Method to perform rule activation and send requirements to other nodes.

        Args:
            memories_info (list[MemoryInfo]): list of memories infos for memories meeting requirements.
        """

        protocol, req_dsts, req_condition_funcs, req_args = self.action(memories_info, self.action_args)
        log.logger.info('{} rule generates protocol {}'.format(self.rule_manager, protocol.name))

        protocol.rule = self  # the protocol is connected to the reservation via the rule
        self.protocols.append(protocol)
        for info in memories_info:
            info.memory.detach(info.memory.memory_array)
            info.memory.attach(protocol)
        for dst, req_func, args in zip(req_dsts, req_condition_funcs, req_args):
            self.rule_manager.send_request(protocol, dst, req_func, args)

    def is_valid(self, memory_info: "MemoryInfo") -> list["MemoryInfo"]:
        """Method to check for memories meeting condition.

        Args:
            memory_info (MemoryInfo): memories info object to test.

        Returns:
            list[memory_info]: list of memories info objects meeting requirements of rule.
        """

        manager = self.rule_manager.get_memory_manager()
        return self.condition(memory_info, manager, self.condition_args)

    def set_reservation(self, reservation: "Reservation") -> None:
        self.reservation = reservation

    def get_reservation(self) -> "Reservation":
        return self.reservation
