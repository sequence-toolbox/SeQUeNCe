"""Entanglement protocol definition (abstract)"""

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import Node
    from ..components.memory import Memory

from ..protocol import Protocol


class EntanglementProtocol(Protocol):
    """Class for all entanglement management protocols.

    Provides an interface for rule attachment, protocol pairing, and memory management.

    Attributes:
        own (Node): Node object to attach to
        name (str): Name of the protocol instance
        rule (Rule): Rule which created this protocol instance (from the rule manager)
        memories (List[Memory]): Any memories being operated on
    """

    def __init__(self, own: "Node", name: str):
        Protocol.__init__(self, own, name)
        self.rule = None
        self.memories = []

    @abstractmethod
    def set_others(self, other: "EntanglementProtocol") -> None:
        pass

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass

    @abstractmethod
    def memory_expire(self, memory: "Memory") -> None:
        pass

    def release(self) -> None:
        pass
