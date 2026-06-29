"""Definition of Static Routing protocol.

This module defines the StaticRouting protocol, which uses a pre-generated static routing table to direct reservation hops.
Routing tables may be created manually, or generated and installed automatically by the `Topology` class.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...topology.node import QuantumRouter

from .routing_base import RoutingProtocol, ROUTING_STATIC
from ...message import Message


@RoutingProtocol.register(ROUTING_STATIC)
class StaticRoutingProtocol(RoutingProtocol):
    """Class to update forwarding table manually.

    The `StaticRoutingProtocol` class writes to the forwarding table (from the `NetworkManager`).
    Static in this context means that the forwarding table is manually configured (by a network administrator), 
    not automatically updated via a routing protocol (i.e. computer program).
    """
    
    def __init__(self, owner: QuantumRouter, name: str):
        """Constructor for routing protocol.

        Args:
            owner (QuantumRouter): node protocol is attached to.
            name (str): name of protocol instance.
        """
        super().__init__(owner, name, protocol_type=ROUTING_STATIC)

    def init(self):
        pass

    def received_message(self, src: str, msg: "Message"):
        """Method to directly receive messages from node (should not be used)."""

        raise Exception("StaticRouting protocol should not call this function")
