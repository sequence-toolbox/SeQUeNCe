"""Forwarding protocol and forwarding message.

This module defines the `ForwardingProtocol` and `ForwardingMessage` classes.
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..topology.node import Node

from enum import Enum
from ..protocol import StackProtocol
from ..message import Message
from ..utils import log


class ForwardingMessage(Message):
    """Message used for communications between forwarding protocol instances.

    Attributes:
        msg_type (Enum): type of message, required by base `Message` class.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be delivered to destination.
    """

    def __init__(self, msg_type: Enum, receiver: str, payload: Message):
        super().__init__(msg_type, receiver)
        self.payload = payload

    def __str__(self):
        return f"type={self.msg_type}, receiver={self.receiver}, payload={self.payload}"


class ForwardingProtocol(StackProtocol):
    """Class to forward messages based on the forwarding table (from the `NetworkManager`) in the routing protocol.

    Attributes:
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
    """

    def __init__(self, owner: "Node", name: str):
        """Constructor for forwarding protocol.

        Args:
            owner (Node): node protocol is attached to.
            name (str): name of protocol instance.
        """
        super().__init__(owner, name)

    @property
    def forwarding_table(self) -> dict[str, str]:
        """Returns the forwarding table."""
        return self.owner.network_manager.get_forwarding_table()

    def received_message(self, src: str, msg: Message):
        """Method to directly receive messages from node (should not be used)."""

        raise Exception("Forwarding protocol should not call this function")

    def init(self):
        pass

    def push(self, dst: str, msg: Message, next_hop: str = None):
        """Method to receive message from upper protocols.

        Routing packages the message and forwards it to the next node in the optimal path (determined by the forwarding table).

        Args:
            dst (str): name of destination node. If not None, resort to the forwarding table to get the next hop.
            msg (Message): message to relay.
            next_hop (str): name of next hop. If dst is None, next_hop shouldn't be None. next_hop directly tells the next hop.

        Side Effects:
            Will invoke `push` method of lower protocol or network manager.
        """
        assert dst != self.owner.name
        forwarding_table = self.forwarding_table
        new_msg = ForwardingMessage(Enum, self.name, msg)
        if dst:                                     # if dst is not None, use the forwarding table
            next_hop = forwarding_table.get(dst, None)
            if next_hop:
                self._push(dst=next_hop, msg=new_msg)
            else:
                log.logger.error(f'No forwarding rule for dst {dst} at node {self.owner.name}')
        elif next_hop:                              # if next_hop is not None, use next_hop
            self._push(dst=next_hop, msg=new_msg)  
        else:
            raise Exception('Both dst and next_hop are None!')

    def pop(self, src: str, msg: ForwardingMessage):
        """Message to receive reservation messages.

        Messages are forwarded to the upper protocol.

        Args:
            src (str): node sending the message.
            msg (ForwardingMessage): message received.

        Side Effects:
            Will call `pop` method of higher protocol.
        """
        self._pop(src=src, msg=msg.payload)
