"""Definition of the Network Manager.

This module defines the NetworkManager ABC and the default NetworkManager, DistributedNetworkManager.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from sequence.utils.log import logger

from ..components.memory import MemoryArray

if TYPE_CHECKING:
    from ..protocol import StackProtocol
    from ..topology.node import QuantumRouter

from ..message import Message
from ..protocol import Protocol
from ..utils import log
from .forwarding import ForwardingProtocol
from .memory_timecard import MemoryTimeCard
from .reservation import Reservation
from .routing_distributed import DistributedRoutingProtocol
from .routing_static import StaticRoutingProtocol
from .rsvp import RSVPMessage, RSVPMsgType, RSVPProtocol


class NetworkManagerMsgType(Enum):
    OUTBOUND = auto()

class NetworkManagerMessage(Message):
    """Message used by the network manager.

    Attributes:
        msg_type (Enum): message type required by base message type.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be passed through destination network manager.
    """

    def __init__(self, msg_type: Enum, receiver: str, payload):
        super().__init__(msg_type, receiver)
        self.payload = payload

    def __str__(self) -> str:
        return f"type={self.msg_type}; receiver={self.receiver}; payload={self.payload}"


class NetworkManager(ABC):
    """Network Manager Abstraction
    Has the following responsibilities: Take in a reservation request, complete scheduling in some manner, receive the
    decided path, and finally inform the ResourceManager to create Rules.
    
    Attributes:
        name (str): name of the network manager instance.
        owner (QuantumRouter): node that network manager is attached to.
        memory_array_name (str): name of the memory array component in the node.
        memo_arr (MemoryArray): reference to the memory array component in the node.
        timecards (list[MemoryTimeCard]): list of timecards for each memory in the node, 
                                          each timecard is associated with a memory in the memory array.
    """
    _registry: dict[str, type['NetworkManager']] = {}
    _global_type: str = 'distributed'

    def __init__(self, owner: QuantumRouter, memory_array_name: str, **kwargs):
        if kwargs:
            logger.warning(f'Network Manager ABC received kwargs: {list(kwargs.keys())}, ignoring.')
        self.name: str = 'network_manager'
        self.owner = owner
        self.memory_array_name = memory_array_name
        self.memo_arr: MemoryArray = owner.components[memory_array_name]
        self.timecards: list[MemoryTimeCard] = [MemoryTimeCard(i) for i in range(len(self.memo_arr))]

    @classmethod
    def register(cls, name, network_manager_cls=None):
        if network_manager_cls is not None:
            cls._registry[name] = network_manager_cls
            return None

        def decorator(network_manager_cls_dec: type['NetworkManager']):
            cls._registry[name] = network_manager_cls_dec
            return network_manager_cls_dec
        return decorator

    @classmethod
    def create(cls, owner, memory_array_name: str, **kwargs: Any) -> 'NetworkManager':
        """Factory method to create network manager instance based on global type.
        
        Args:
            owner (QuantumRouter): node that network manager is attached to.
            memory_array_name (str): name of the memory array component in the node.
            **kwargs: additional arguments to pass to the network manager constructor.
        
        Returns:
            NetworkManager: instance of network manager based on global type.
        """
        network_manager_cls: type['NetworkManager'] = cls._registry[cls._global_type]
        return network_manager_cls(owner, memory_array_name, **kwargs)

    @classmethod
    def set_global_type(cls, network_manager_type: str) -> None:
        if network_manager_type not in cls._registry:
            raise NotImplementedError(f'Network Manager {network_manager_type} is not registered.')
        else:
            cls._global_type = network_manager_type

    @abstractmethod
    def received_message(self, src: str, msg: NetworkManagerMessage):
        """Handle Message received into the NetworkManager."""
        pass

    @abstractmethod
    def request(self, responder, start_time, end_time, memory_size, target_fidelity, entanglement_number=1, identity=0):
        """Handle Requests from the Application."""
        pass

    def push(self, dst: str, msg: NetworkManagerMessage):
        self.owner.send_message(dst, msg)

    def get_timecards(self):
        return self.timecards

    def generate_rules(self, reservation: Reservation):
        """Generate and load rules for a given reservation.

        Args:
            reservation (Reservation): reservation for which to generate rules.
        """
        self.owner.resource_manager.generate_load_rules(reservation.path, reservation, self.timecards, self.memory_array_name)

@NetworkManager.register('distributed')
class DistributedNetworkManager(NetworkManager):
    """The default Network Manager implementation.

    Attributes:
        protocol_stack (list[StackProtocol]): list of protocols in the network manager stack, ordered from lowest to highest.
        forwarding_table (dict[str, str]): mapping of destination node to next hop for forwarding.
        routing_protocol (Protocol): protocol used for updating forwarding table.
    """
    def __init__(self, owner: "QuantumRouter", memory_array_name: str, component_templates=None):
        super().__init__(owner, memory_array_name)
        if component_templates is None:
            component_templates = {}
        self.protocol_stack = []
        self.forwarding_table = {}
        self.routing_protocol = self._create_routing_protocol(component_templates.get('routing', 'static'))
        # Create and load the stack to protocol_stack
        protocols: list = self.create_stack()
        self.load_stack(protocols)

    @property
    def rsvp(self):
        return self.protocol_stack[-1]

    @property
    def forward(self):
        return self.protocol_stack[0]

    def get_forwarding_table(self) -> dict[str, str]:
        """Returns the forwarding table.
        
        Returns:
            dict[str, str]: forwarding table mapping destination node to next hop.
        """
        return self.forwarding_table

    def set_forwarding_table(self, forwarding_table: dict):
        """Set the forwarding table for the network manager.

        Args:
            forwarding_table (dict): mapping of destination node to next hop.
        """
        log.logger.info(f'{self.owner.name} set forwarding table: {forwarding_table}')
        self.forwarding_table = forwarding_table

    def get_routing_protocol(self):
        return self.routing_protocol

    def _create_routing_protocol(self, routing_type) -> Protocol:
        """Helper function to create routing protocol based on routing type.

        Args:
            routing_type (str): type of routing protocol to create, i.e., 'static' or 'distributed'.
        """
        match routing_type:
            case 'static':
                routing_protocol_cls = StaticRoutingProtocol
            case 'distributed':
                routing_protocol_cls = DistributedRoutingProtocol
            case _:
                raise NotImplementedError(f'Routing protocol {routing_type} is not implemented.')
        return routing_protocol_cls(self.owner, f'{routing_protocol_cls.__name__}')

    def create_stack(self) -> list[StackProtocol]:
        """Helper function to stand up the protocols
        
        Returns:
            list[StackProtocol]: list of protocol instances in the stack, ordered from lowest to highest.
        """
        rsvp = RSVPProtocol(self.owner, f'{self.owner.name}.RSVP', self.memory_array_name)
        forwarding_protocol = ForwardingProtocol(self.owner, f'{self.owner.name}.ForwardingProtocol')
        rsvp.timecards = self.timecards
        forwarding_protocol.upper_protocols.append(rsvp)
        rsvp.lower_protocols.append(forwarding_protocol)
        return [forwarding_protocol, rsvp]

    def load_stack(self, stack: "list[StackProtocol]"):
        """Method to load a defined protocol stack.

        Args:
            stack (list[StackProtocol]): New protocol stack.
        """
        self.protocol_stack = stack
        if len(self.protocol_stack) > 0:
            self.forward.lower_protocols.append(self)
            self.rsvp.upper_protocols.append(self)

    def push(self, dst: str, msg: Message):
        """Push a message. This is an OUTBOUND message that will be sent to another node.

        Args:
            dst (str): destination node of the message.
            msg (Message): message to be sent.
        """
        outbound_msg = NetworkManagerMessage(NetworkManagerMsgType.OUTBOUND, 'network_manager', msg)
        super().push(dst, outbound_msg)

    def pop(self, msg: RSVPMessage):
        """Pop a message. This is an INBOUND message coming from its internal RSVP protocol.
        
        Args:
            msg (RSVPMessage): message received from another node.
        """
        reservation: Reservation = msg.reservation
        if msg.msg_type == RSVPMsgType.APPROVE:
            self.generate_rules(reservation)
            if reservation.initiator == self.owner.name:
                self.owner.get_reservation_result(reservation, True) # Deliver the result to the Node
            elif reservation.responder == self.owner.name:
                self.owner.get_other_reservation(reservation)
        elif msg.msg_type == RSVPMsgType.REJECT:
            if reservation.initiator == self.owner.name:
                self.owner.get_reservation_result(reservation, False)

    def received_message(self, src: str, msg: NetworkManagerMessage):
        """Handle Message received from another node that is directed into the NetworkManager.

        Args:
            src (str): name of source node that sent the message.
            msg (NetworkManagerMessage): the message received from the source node.
        """
        log.logger.info(f'{self.owner.name} network manager received message from {src}: {msg}')
        self.forward.pop(src=src, msg=msg.payload)

    def request(self, responder, start_time, end_time, memory_size, target_fidelity, entanglement_number=1, identity=0):
        """Handle Requests from the Application by pushing the request into the stack.
           The RSVP protocol at the top of the stack will handle it.
        
        Args:
            responder (str): name of node with which entanglement is requested.
            start_time (int): reservation start time in picoseconds.
            end_time (int): reservation end time in picoseconds.
            memory_size (int): number of entangled memories requested (at the initiator and responder).
            target_fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement pairs the request ask for.
            identity (int): the ID of a request
        """
        self.rsvp.push(responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity)
