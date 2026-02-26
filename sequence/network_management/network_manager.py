"""Definition of the Network Manager.

This module defines the NetworkManager class, an implementation of the SeQUeNCe network management module.
Also included in this module is the message type used by the network manager and a function for generating network managers with default protocols.
"""
from __future__ import annotations
from sequence.utils.log import logger
from abc import abstractmethod, ABC
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from ..components.memory import MemoryArray

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..protocol import StackProtocol

from ..message import Message
from ..protocol import Protocol
from .routing_distributed import DistributedRoutingProtocol
from .routing_static import StaticRoutingProtocol
from .forwarding import ForwardingProtocol
from .reservation import Reservation
from .rsvp import RSVPProtocol, RSVPMsgType
from .memory_timecard import MemoryTimeCard
from ..utils import log

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
    decided path, and finally inform the ResourceManager to create Rules."""
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
    def request(self, responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity):
        """Handle Requests from the Application."""
        pass

    def push(self, dst: str, msg: NetworkManagerMessage):
        self.owner.send_message(dst, msg)

    def get_timecards(self):
        return self.timecards

    def generate_rules(self, reservation: Reservation):
        self.owner.resource_manager.generate_load_rules(reservation.path, reservation, self.timecards,
                                                        self.memory_array_name)

@NetworkManager.register('distributed')
class DistributedNetworkManager(NetworkManager):
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

    def get_forwarding_table(self) -> dict[str, str]:
        return self.forwarding_table

    def set_forwarding_table(self, forwarding_table: dict):
        log.logger.info(f'{self.owner.name} set forwarding table: {forwarding_table}')
        self.forwarding_table = forwarding_table

    def get_routing_protocol(self):
        return self.routing_protocol

    def _create_routing_protocol(self, routing_type) -> Protocol:
        match routing_type:
            case 'static':
                routing_protocol_cls = StaticRoutingProtocol
            case 'distributed':
                routing_protocol_cls = DistributedRoutingProtocol
            case _:
                raise NotImplementedError(f'Routing protocol {routing_type} is not implemented.')
        return routing_protocol_cls(self.owner, f'{routing_protocol_cls.__name__}')

    def create_stack(self):
        """Helper function to stand up the protocols"""
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
            self.protocol_stack[0].lower_protocols.append(self)
            self.protocol_stack[-1].upper_protocols.append(self)

    def push(self, **kwargs):
        outbound_msg = NetworkManagerMessage(Enum, 'network_manager', kwargs['msg'])
        self.owner.send_message(kwargs['dst'], outbound_msg)

    def pop(self, **kwargs):
        inbound_msg = kwargs['msg']
        log.logger.info(f'{self.owner.name} DNM.pop: msg_type={inbound_msg.msg_type}, reservation={inbound_msg.reservation}')
        reservation = inbound_msg.reservation
        if inbound_msg.msg_type == RSVPMsgType.APPROVE:
            self.generate_rules(reservation)
            if reservation.initiator == self.owner.name:
                self.owner.get_reservation_result(reservation, True) # Deliver the result to the Node
            elif reservation.responder == self.owner.name:
                self.owner.get_other_reservation(reservation)
        elif inbound_msg.msg_type == RSVPMsgType.REJECT:
            if reservation.initiator == self.owner.name:
                self.owner.get_reservation_result(reservation, False)


    def received_message(self, src: str, msg: NetworkManagerMessage):
        log.logger.info(f'{self.owner.name} network manager received message from {src}: {msg}')
        self.protocol_stack[0].pop(src=src, msg=msg.payload)

    def request(self, responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity):
        self.protocol_stack[-1].push(responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity)
