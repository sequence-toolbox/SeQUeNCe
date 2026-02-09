"""Definition of abstract protocol type.

This module defines the protocol type inherited by all protocol code implementations.
Also defined is the stack protocol, which adds push and pop functionality.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .topology.node import Node
    from .message import Message


class Protocol(ABC):
    """Abstract protocol class for code running on network nodes.

    Attributes:
        own (Node): node protocol is attached to.
        name (str): label for protocol instance.
    """

    def __init__(self, owner: "Node", name: str):
        """Constructor for protocol.

        Args:
            owner (Node): node protocol is attached to.
            name (str): name of protocol instance.
        """

        self.owner = owner
        self.name = name

    @abstractmethod
    def received_message(self, src: str, msg: "Message"):
        """Receive classical message from another node."""

        pass

    def __str__(self) -> str:
        return self.name


class StackProtocol(Protocol):
    """Abstract protocol class for protocols in a stack structure.

    Adds interfaces for push and pop functions.

    Attributes:
        owner (Node): node protocol is attached to.
        name (str): label for protocol instance.
        upper_protocols (list[StackProtocol]): Protocols to pop to.
        lower_protocols (list[StackProtocol]): Protocols to push to.
    """

    def __init__(self, owner: "Node", name: str):
        """Constructor for stack protocol class.

        Args:
            owner (Node): node protocol is attached to.
            name (str): name of protocol instance.
        """

        super().__init__(owner, name)
        self.upper_protocols = []
        self.lower_protocols = []

    @abstractmethod
    def push(self, *args, **kwargs) -> None:
        """Method to receive information from protocols higher on the stack (abstract)."""

        pass

    @abstractmethod
    def pop(self, *args, **kwargs) -> None:
        """Method to receive information from protocols lower on the stack (abstract)."""

        pass

    def _push(self, *args, **kwargs) -> None:
        """call the push of all lower_protocols"""
        for protocol in self.lower_protocols:
            protocol.push(*args, **kwargs)

    def _pop(self, *args, **kwargs) -> None:
        """call the pop of all upper_protocols"""
        for protocol in self.upper_protocols:
            protocol.pop(*args, **kwargs)

    def received_message(self, src: str, msg: "Message"):
        """Method to receive messages from distant nodes."""

        pass
