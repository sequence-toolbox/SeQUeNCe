"""
The base class for routing protocols.
All routing protocols should inherit from this class and implement the required methods.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...topology.node import QuantumRouter

from ...message import Message
from ...protocol import Protocol
from ...utils import log


# type labels for routing protocols:
ROUTING_STATIC      = 'routing_static'
ROUTING_DISTRIBUTED = 'routing_distributed'


class RoutingProtocol(Protocol, ABC):
    """Abstract base class for routing protocols.
    """
    _registry: dict[str, type[RoutingProtocol]] = {}
    _global_type: str = ROUTING_STATIC

    def __init__(self, owner: QuantumRouter, name: str, protocol_type: str):
        """Constructor for routing protocol.

        Args:
            owner (QuantumRouter): node protocol is attached to.
            name (str): name of protocol instance.
            protocol_type (str): type of the routing protocol.
        """
        super().__init__(owner, name, protocol_type)

    @classmethod
    def set_global_type(cls, protocol_type: str):
        """Set the global routing protocol type.

        Args:
            protocol_type (str): type of the routing protocol.
        """
        if protocol_type not in cls._registry:
            raise ValueError(f"Routing protocol type {protocol_type} not registered.")
        cls._global_type = protocol_type

    @classmethod
    def get_global_type(cls) -> str:
        """Get the global routing protocol type.

        Returns:
            str: global routing protocol type.
        """
        return cls._global_type
    
    @classmethod
    def register(cls, protocol_type: str, protocol_class: type[RoutingProtocol] = None):
        """Register a routing protocol class.

        Args:
            protocol_type (str): type of the routing protocol.
            protocol_class (type['RoutingProtocol']): class of the routing protocol. Defaults to None.
        """
        if protocol_class is not None:
            cls._registry[protocol_type] = protocol_class
            return None
        
        def decorator(protocol_class: type[RoutingProtocol]):
            cls._registry[protocol_type] = protocol_class
            return protocol_class

        return decorator

    @classmethod
    def create(cls, owner: QuantumRouter, name: str) -> RoutingProtocol:
        """Factory method to create a routing protocol instance.

        Args:
            owner (QuantumRouter): node protocol is attached to.
            name (str): name of protocol instance.
            protocol_type (str): type of the routing protocol. If None, use global type.

        Returns:
            RoutingProtocol: instance of the routing protocol.
        """
        protocol_type = cls._global_type
        try:
            protocol_class = cls._registry[protocol_type]
            return protocol_class(owner, name)
        except KeyError:
            raise ValueError(f"Routing protocol type {protocol_type} not registered.")

    @abstractmethod
    def init(self):
        """Initialize routing protocol. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def received_message(self, src: str, msg: Message):
        """Method to handle received messages. Must be implemented by subclasses."""
        pass

    @property
    def forwarding_table(self) -> dict[str, str]:
        """Returns the forwarding table.
        
        Returns:
            dict[str, str]: forwarding table in format {name of destination node: name of next node}.
        """
        return self.owner.network_manager.get_forwarding_table()
    
    def update_forwarding_rule(self, dst: str, next_node: str):
        """Updates dst to map to next_node in forwarding table.
           If dst not in forwarding table, effectively adds a new rule to the forwarding table.

        Args:
            dst (str): name of destination node.
            next_node (str): name of next hop node.
        """
        forwarding_table = self.forwarding_table
        forwarding_table[dst] = next_node
        log.logger.debug(f'Updated forwarding rule at node {self.owner.name}: {dst} -> {next_node}')

    def set_forwarding_table(self, forwarding_table: dict[str, str]):
        """Sets the whole forwarding table.

        Args:
            forwarding_table (dict[str, str]): forwarding table in format {name of destination node: name of next node}.
        """
        self.owner.network_manager.set_forwarding_table(forwarding_table)
        log.logger.debug(f'Set forwarding table at node {self.owner.name} to: {forwarding_table}')
