from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...topology.node import Node
    from ..message import Message

from .memory_manager import *
from .ruleset import *


class ResourceManager():
    def __init__(self, owner: "Node"):
        self.name = "resource_manager"
        self.owner = owner
        self.tracer = MemoryManager()
        self.ruleset = Ruleset()

    def load(self, rule: "Rule") -> bool:
        return self.ruleset.load(rule)

    def update(self, protocol, memory: "Memory", state) -> bool:
        self.tracer.update(memory, state)
        self.owner.protocols.remove(protocol)

        # check if any rules have been met
        for rule in self.ruleset:
            if rule.is_valid:
                rule.do
                return True

        return False

    def received_message(self, src: str, msg: "Message") -> None:
        pass
