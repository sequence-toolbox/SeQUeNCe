"""Definition of Routing protocol.

This module defines the StaticRouting protocol, which uses a pre-generated static routing table to direct reservation hops.
Routing tables may be created manually, or generated and installed automatically by the `Topology` class.
Also included is the message type used by the routing protocol.
"""

from enum import Enum
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from ..topology.node import Node

from ..message import Message
from ..protocol import StackProtocol


class StaticRoutingMessage(Message):
    """Message used for communications between routing protocol instances.

    Attributes:
        msg_type (Enum): type of message, required by base `Message` class.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be delivered to destination.
    """

    def __init__(self, msg_type: Enum, receiver: str, payload: "Message"):
        super().__init__(msg_type, receiver)
        self.payload = payload

    def __str__(self):
        return "type={}, receiver={}, payload={}".format(self.msg_type,
                                                         self.receiver,
                                                         self.payload)


class StaticRoutingProtocol(StackProtocol):
    """Class to route reservation requests.

    The `StaticRoutingProtocol` class uses a static routing table to direct the flow of reservation requests.
    This is usually defined based on the shortest quantum channel length.

    Attributes:
        own (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
        forwarding_table (Dict[str, str]): mapping of destination node names to name of node for next hop.
    """
    
    def __init__(self, own: "Node", name: str, forwarding_table: Dict):
        """Constructor for routing protocol.

        Args:
            own (Node): node protocol is attached to.
            name (str): name of protocol instance.
            forwarding_table (Dict[str, str]): forwarding routing table in format {name of destination node: name of next node}.
        """

        super().__init__(own, name)
        self.forwarding_table = forwarding_table

    def add_forwarding_rule(self, dst: str, next_node: str):
        """Adds mapping {dst: next_node} to forwarding table."""

        assert dst not in self.forwarding_table
        self.forwarding_table[dst] = next_node

    def update_forwarding_rule(self, dst: str, next_node: str):
        """updates dst to map to next_node in forwarding table."""

        self.forwarding_table[dst] = next_node

    def push(self, dst: str, msg: "Message"):
        """Method to receive message from upper protocols.

        Routing packages the message and forwards it to the next node in the optimal path (determined by the forwarding table).

        Args:
            dst (str): name of destination node.
            msg (Message): message to relay.

        Side Effects:
            Will invoke `push` method of lower protocol or network manager.
        """

        assert dst != self.own.name
        dst = self.forwarding_table[dst]
        new_msg = StaticRoutingMessage(Enum, self.name, msg)
        self._push(dst=dst, msg=new_msg)

    def pop(self, src: str, msg: "StaticRoutingMessage"):
        """Message to receive reservation messages.

        Messages are forwarded to the upper protocol.

        Args:
            src (str): node sending the message.
            msg (StaticRoutingMessage): message received.

        Side Effects:
            Will call `pop` method of higher protocol.
        """

        self._pop(src=src, msg=msg.payload)

    def received_message(self, src: str, msg: "Message"):
        """Method to directly receive messages from node (should not be used)."""

        raise Exception("RSVP protocol should not call this function")

    def init(self):
        pass
