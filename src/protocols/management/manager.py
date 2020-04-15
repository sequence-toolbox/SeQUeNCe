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
        pass

    def update(self, memory: "Memory", state) -> bool:
        pass

    def received_message(self, src: str, msg: "Message") -> None:
        pass
