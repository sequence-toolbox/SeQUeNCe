"""Forwarding protocol and forwarding a message.

This module defines the `ForwardingProtocol` and `ForwardingMessage` classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter

from enum import Enum

from ..message import Message
from ..protocol import StackProtocol
from ..utils import log


class ForwardingMessage(Message):
    """Message used for communications between forwarding protocol instances.

    Attributes:
        msg_type (Enum): type of message, required by base `Message` class.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be delivered to destination.
    """

    def __init__(self, msg_type: type[Enum], receiver: str, payload: Message):
        super().__init__(msg_type, receiver)
        self.payload: Message = payload

    def __str__(self):
        return f"type={self.msg_type}, receiver={self.receiver}, payload={self.payload}"


class ForwardingProtocol(StackProtocol):
    """Class to forward messages based on the forwarding table (from the `NetworkManager`) in the routing protocol.

    Attributes:
        owner (QuantumRouter): node that the protocol instance is attached to.
        name (str): label for protocol instance.
    """

    def __init__(self, owner: QuantumRouter, name: str):
        """Constructor for forwarding protocol.

        Args:
            owner (QuantumRouter): node protocol is attached to.
            name (str): name of protocol instance.
        """
        self.owner: QuantumRouter = owner
        self.name: str = name
        super().__init__(owner, name)

    @property
    def forwarding_table(self) -> dict[str, str]:
        """Returns the forwarding table."""
        assert self.owner.network_manager is not None
        return self.owner.network_manager.get_forwarding_table()

    def received_message(self, src: str, msg: Message):
        """Method to directly receive messages from a node (should not be used)."""

        raise Exception("Forwarding protocol should not call this function")

    def init(self):
        pass

    def push(self, dst: str, msg: Message, next_hop: str | None = None):
        """Method to receive a message from upper protocols.

        Routing packages the message and forwards it to the next node in the optimal path (determined by the forwarding table).

        Args:
            dst (str): name of the destination node. If not None, resort to the forwarding table to get the next hop.
            msg (Message): message to relay.
            next_hop (str): name of next hop. If dst is None, next_hop shouldn't be None. next_hop directly tells the next hop.

        Side Effects:
            Will invoke `push` method of lower protocol or network manager.
        """
        assert dst != self.owner.name
        forwarding_table = self.forwarding_table
        new_msg = ForwardingMessage(Enum, self.name, msg)
        if dst:  # if dst is not None, use the forwarding table
            next_hop = forwarding_table.get(dst, None)
            if next_hop:
                self._push(dst=next_hop, msg=new_msg)
            else:
                log.logger.error(
                    f"No forwarding rule for dst {dst} at node {self.owner.name}"
                )
        elif next_hop:  # if next_hop is not None, use next_hop
            self._push(dst=next_hop, msg=new_msg)
        else:
            raise Exception("Both dst and next_hop are None!")

    def pop(self, src: str, msg: Message) -> None:
        """Message to receive reservation messages.

        Messages are forwarded to the upper protocol.

        Args:
            src (str): node sending the message.
            msg (Message): message received.

        Side Effects:
            Will call `pop` method of higher protocol.
        """
        self._pop(src=src, msg=msg.payload)
