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

    def __init__(self, own: "Node", name: str):
        """Constructor for protocol.

        Args:
            own (Node): node protocol is attached to.
            name (str): name of protocol instance.
        """

        self.own = own
        self.name = name

    @abstractmethod
    def received_message(self, src: str, msg: "Message"):
        """Receive classical message from another node."""

        pass


class StackProtocol(Protocol):
    """Abstract protocol class for protocols in a stack structure.

    Adds interfaces for push and pop functions.

    Attributes:
        own (Node): node protocol is attached to.
        name (str): label for protocol instance.
        upper_protocols (List[StackProtocol]): Protocols to pop to.
        lower_protocols (List[StackProtocol]): Protocols to push to.
    """

    def __init__(self, own: "Node", name: str):
        """Constructor for stack protocol class.

        Args:
            own (Node): node protocol is attached to.
            name (str): name of protocol instance.
        """

        super().__init__(own, name)
        self.upper_protocols = []
        self.lower_protocols = []

    @abstractmethod
    def push(self, **kwargs):
        """Method to receive information from protocols higher on stack (abstract)."""

        pass

    @abstractmethod
    def pop(self, **kwargs):
        """Method to receive information from protocols lower on stack (abstract)."""

        pass

    def _push(self, **kwargs):
        for protocol in self.lower_protocols:
            protocol.push(**kwargs)

    def _pop(self, **kwargs):
        for protocol in self.upper_protocols:
            protocol.pop(**kwargs)

    def received_message(self, src: str, msg: "Message"):
        """Method to receive messages from distant nodes."""

        pass
