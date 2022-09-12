"""Entanglement protocol definition (abstract)"""

from abc import abstractmethod
from typing import TYPE_CHECKING, List

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
        rule (Rule): Rule which created this protocol instance (from the rule manager).
        memories (List[Memory]): Any memories being operated on
    """

    def __init__(self, own: "Node", name: str):
        Protocol.__init__(self, own, name)
        self.rule = None
        self.memories = []

    @abstractmethod
    def set_others(self, remote_protocol: str, remote_node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            remote_protocol (str): other protocol name.
            remote_node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """

        pass

    @abstractmethod
    def start(self) -> None:
        """Method to start entanglement protocol process (abstract)."""

        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Method to check if protocol is ready to start (abstract).

        Returns:
            bool: if protocol is ready or not.
        """

        pass

    @abstractmethod
    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive a memory expiration event (abstract)."""

        pass

    def release(self) -> None:
        """Method to release attached memories."""

        pass

    def update_resource_manager(self, memory: "Memory", state: str) -> None:
        """Method to update attached memory to desired state.

        Args:
            memory (Memory): attached memory to update.
            state (str): state memory should be updated to.

        Side Effects:
            May alter the state of `memory`.
        """

        self.own.resource_manager.update(self, memory, state)

