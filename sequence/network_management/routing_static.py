"""Definition of Static Routing protocol.

This module defines the StaticRouting protocol, which uses a pre-generated static routing table to direct reservation hops.
Routing tables may be created manually, or generated and installed automatically by the `Topology` class.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import Node

from ..message import Message
from ..protocol import Protocol
from ..utils import log


class StaticRoutingProtocol(Protocol):
    """Class to update forwarding table manually.

    The `StaticRoutingProtocol` class writes to the forwarding table (from the `NetworkManager`).
    Static in this context means that the forwarding table is manually configured (by a network administrator), 
    not automatically updated via a routing protocol (i.e. computer program).

    Attributes:
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
    """
    
    def __init__(self, owner: "Node", name: str):
        """Constructor for routing protocol.

        Args:
            owner (Node): node protocol is attached to.
            name (str): name of protocol instance.
        """
        super().__init__(owner, name)
        self.protocol_type = 'routing_static'
    
    @property
    def forwarding_table(self) -> dict[str, str]:
        """Returns the forwarding table.
        
        Returns:
            dict[str, str]: forwarding table in format {name of destination node: name of next node}.
        """
        return self.owner.network_manager.get_forwarding_table()

    def add_forwarding_rule(self, dst: str, next_node: str):
        """Adds mapping {dst: next_node} to forwarding table.
        
        Args:
            dst (str): name of destination node.
            next_node (str): name of next hop node.
        """
        forwarding_table = self.forwarding_table
        if dst not in forwarding_table:
            forwarding_table[dst] = next_node
            log.logger.info(f'Added forwarding rule at node {self.owner.name}: {dst} -> {next_node}')

    def update_forwarding_rule(self, dst: str, next_node: str):
        """updates dst to map to next_node in forwarding table.
        
        Args:
            dst (str): name of destination node.
            next_node (str): name of next hop node.
        """
        forwarding_table = self.forwarding_table
        if dst in forwarding_table:
            forwarding_table[dst] = next_node
            log.logger.info(f'Updated forwarding rule at node {self.owner.name}: {dst} -> {next_node}')

    def received_message(self, src: str, msg: "Message"):
        """Method to directly receive messages from node (should not be used)."""

        raise Exception("StaticRouting protocol should not call this function")

    def init(self):
        pass
