"""Definition of Routing protocol.

This module defines the StaticRouting protocol, which uses a pre-generated static routing table to direct reservation hops.
Routing tables may be created manually, or generated and installed automatically by the Topology class.
Also included is the message type used by the routing protocol.
"""

from enum import Enum
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from ..topology.node import Node

from ..message import Message
from ..protocol import StackProtocol


class StaticRoutingMessage(Message):
    def __init__(self, msg_type: Enum, receiver: str, payload: "Message"):
        super().__init__(msg_type, receiver)
        self.payload = payload


class StaticRoutingProtocol(StackProtocol):
    def __init__(self, own: "Node", name: str, forwarding_table: Dict):
        '''
        forwarding_table: {name of destination node: name of next node}
        '''
        super().__init__(own, name)
        self.forwarding_table = forwarding_table

    def add_forwarding_rule(self, dst: str, next_node: str):
        assert dst not in self.forwarding_table
        self.forwarding_table[dst] = next_node

    def update_forwarding_rule(self, dst: str, next_node: str):
        self.forwarding_table[dst] = next_node

    def push(self, dst: str, msg: "Message"):
        assert dst != self.own.name
        dst = self.forwarding_table[dst]
        new_msg = StaticRoutingMessage(Enum, self.name, msg)
        self._push(dst=dst, msg=new_msg)

    def pop(self, src: str, msg: "StaticRoutingMessage"):
        self._pop(src=src, msg=msg.payload)

    def received_message(self, src: str, msg: "Message"):
        raise Exception("RSVP protocol should not call this function")

    def init(self):
        pass
