"""Entanglement protocol definition (abstract)"""

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import Node
    from ..components.memories import Memory

from ..protocol import Protocol


class EntanglementProtocol(Protocol):
    """Class for all entanglement management protocols.

    Provides an interface for rule attachment, protocol pairing, and memories management.

    Attributes:
        own (Node): Node object to attach to
        name (str): Name of the protocol instance
        rule (Rule): Rule which created this protocol instance (from the rule manager).
        memories (list[Memory]): Any memories being operated on
    """

    def __init__(self, owner: "Node", name: str):
        super().__init__(owner, name)
        self.rule = None
        self.memories = []

    @abstractmethod
    def set_others(self, remote_protocol: str, remote_node: str, memories: list[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            remote_protocol (str): other protocol name.
            remote_node (str): other node name.
            memories (list[str]): the list of memories names used on other node.
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
        """Method to receive a memories expiration event (abstract)."""

        pass

    def release(self) -> None:
        """Method to release attached memories."""

        pass

    def update_resource_manager(self, memory: "Memory", state: str) -> None:
        """Method to update attached memories to desired state.

        Args:
            memory (Memory): attached memories to update.
            state (str): state memories should be updated to.

        Side Effects:
            May alter the state of `memories`.
        """

        self.owner.resource_manager.update(self, memory, state)

