"""Definition of the Network Manager.

This module defines the NetworkManager class, an implementation of the SeQUeNCe network management module.
Also included in this module is the message type used by the network manager and a function for generating network managers with default protocols.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, overload, TypeVar, Literal

if TYPE_CHECKING:
    from ..protocol import StackProtocol
    from ..topology.node import QuantumRouter

from ..message import Message
from ..protocol import Protocol
from ..utils import log
from .forwarding import ForwardingProtocol
from .reservation import (
    ResourceReservationMessage,
    ResourceReservationProtocol,
    RSVPMsgType,
)
from .routing_distributed import DistributedRoutingProtocol
from .routing_static import StaticRoutingProtocol

T = TypeVar('T', bound='NetworkManager')

class NetworkManagerMessage(Message):
    """Message used by the network manager.

    Attributes:
        msg_type (Enum): message type required by base message type.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be passed through destination network manager.
    """

    def __init__(self, msg_type: type[Enum], receiver: str, payload: Message):
        super().__init__(msg_type, receiver)
        self.payload: Message = payload

    def __str__(self) -> str:
        return f"type={self.msg_type}; receiver={self.receiver}; payload={self.payload}"

class NetworkManager(ABC):
    _registry: dict[str, type["NetworkManager"]] = {}

    def __init__(self, owner: QuantumRouter, *args, **kwargs):
        """Constructor for network manager.
        Args:
            owner (QuantumRouter): owner of network manager.
        """
        self.owner: QuantumRouter = owner

    @classmethod
    def register(cls, name: str, nm_cls: type["NetworkManager"]=None):
        if nm_cls is not None:
            cls._registry[name] = nm_cls
            return None

        def decorator(dec_nm_cls: type["NetworkManager"]):
            cls._registry[name] = dec_nm_cls
            return dec_nm_cls
        return decorator

    @overload
    @classmethod
    def create(cls, cls_name: Literal['default'], owner: QuantumRouter, protocol_stack: list[StackProtocol]) -> "DefaultNetworkManager": ...

    @overload
    @classmethod
    def create(cls, cls_name: str, owner: QuantumRouter, *args, **kwargs) -> "NetworkManager": ...

    @classmethod
    def create(cls, cls_name: str, owner: QuantumRouter, *args, **kwargs) -> "NetworkManager":
        if cls_name not in cls._registry:
            raise ValueError(f'NetworkManager {cls_name} is not registered.')

        nm_cls: type["NetworkManager"] = cls._registry[cls_name]
        return nm_cls(owner, *args, **kwargs)

    @abstractmethod
    def received_message(self, src: str, msg: NetworkManagerMessage):
        """Method to receive transmitted network reservation method.
        Will pop a message to the lowest protocol in the protocol stack.
        pass
        """

    @abstractmethod
    def request(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float, entanglement_number: int = 1, identity: int = 0) -> None:
        """Method to make an entanglement request. Will defer the request to the top protocol in the protocol stack.
        Args:
            responder (str): name of node to establish entanglement with.
            start_time (int): simulation start time of entanglement.
            end_time (int): simulation end time of entanglement.
            memory_size (int): number of entangled memory pairs to create.
            target_fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement requested.
            identity (int): the ID of the request.
        """
        pass

@NetworkManager.register('default')
class DefaultNetworkManager(NetworkManager):
    """Network manager implementation class.

    The network manager is responsible for the operations of a node within a broader quantum network.
    This is done through a `protocol_stack` of protocols, which messages are passed and packaged through.

    Attributes:
        name (str): name of the network manager instance.
        owner (QuantumRouter): node that protocol instance is attached to.
        protocol_stack (list[StackProtocol]): network manager protocol stack.
        forwarding_table (dict[str, str]): mapping of destination node names to name of node for next hop.
        routing_protocol (Protocol): routing protocol
    """

    def __init__(self, owner: QuantumRouter, protocol_stack: list[StackProtocol]):
        """Constructor for network manager.

        Args:
            owner (QuantumRouter): node network manager is attached to.
            protocol_stack (list[StackProtocol]): stack of protocols to use for processing.
        """

        log.logger.info(f"Create network manager of Node {owner.name}")
        self.name: str = "network_manager"
        self.owner: QuantumRouter = owner
        self.protocol_stack: list[StackProtocol] = protocol_stack
        self.forwarding_table: dict = {}
        self.routing_protocol: Protocol | None = None

        self.load_stack(protocol_stack)

        
    def load_stack(self, stack: list[StackProtocol]):
        """Method to load a defined protocol stack.

        Args:
            stack (list[StackProtocol]): new protocol stack.
        """

        self.protocol_stack = stack

        if len(self.protocol_stack) > 0:
            self.protocol_stack[0].lower_protocols.append(self)
            self.protocol_stack[-1].upper_protocols.append(self)

    def push(self, **kwargs):
        """Method to receive pushes from the lowest protocol in the protocol stack.

        Will create the message to send to another node.

        Keyword Args:
            msg (any): message to deliver.
            dst (str): name of destination node.
        """

        message = NetworkManagerMessage(Enum, "network_manager", kwargs["msg"])
        self.owner.send_message(kwargs["dst"], message)

    def pop(self, **kwargs):
        """Method to receive pops from the highest protocol in the protocol stack.

        Will get reservation from a message and attempt to meet it.

        Keyword Args:
            msg (any): message containing a reservation.
        """

        msg = kwargs.get("msg")
        assert isinstance(msg, ResourceReservationMessage)
        reservation = msg.reservation
        if reservation.initiator == self.owner.name:
            if msg.msg_type == RSVPMsgType.APPROVE:
                self.owner.get_reservation_result(reservation, True)
            else:
                self.owner.get_reservation_result(reservation, False)
        elif reservation.responder == self.owner.name:
            self.owner.get_other_reservation(reservation)

    def received_message(self, src: str, msg: NetworkManagerMessage):
        """Method to receive transmitted network reservation method.

        Will pop a message to the lowest protocol in the protocol stack.

        Args:
            src (str): name of the source node for a message.
            msg (NetworkManagerMessage): message received.

        Side Effects:
            Will invoke `pop` method of 0 indexed protocol in `protocol_stack`.
        """

        log.logger.info(f"{self.owner.name} network manager receives message from {src}: {msg}")
        forwarding_protocol = self.get_forwarding_protocol()
        forwarding_protocol.pop(src=src, msg=msg.payload)

    def request(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float,
                entanglement_number: int = 1, identity: int = 0) -> None:
        """Method to make an entanglement request.

        Will defer the request to the top protocol in the protocol stack.

        Args:
            responder (str): name of node to establish entanglement with.
            start_time (int): simulation start time of entanglement.
            end_time (int): simulation end time of entanglement.
            memory_size (int): number of entangled memory pairs to create.
            target_fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement requested.
            identity (int): the ID of the request.

        Side Effects:
            Will invoke `push` method of -1 indexed protocol in `protocol_stack`,
            which is the resource reservation protocol.
        """
        reservation_protocol = self.get_reservation_protocol()
        reservation_protocol.push(responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity)

    def set_forwarding_table(self, forwarding_table: dict) -> None:
        """Method to set the forwarding table in the network manager

        Args:
            forwarding_table (dict): the forwarding table for this node, where the key is the destination node name
                                     and the value is the next hop
        """
        log.logger.info(f"{self.owner.name} set forwarding table: {forwarding_table}")
        self.forwarding_table = forwarding_table

    def get_forwarding_table(self) -> dict[str, str]:
        """Method to get the forwarding table in the network manager.

        Returns:
            dict[str, str]: the forwarding table for this node, where the key is the destination node name
                            and the value is the next hop
        """
        return self.forwarding_table

    def get_reservation_protocol(self) -> ResourceReservationProtocol:
        """Method to get the resource reservation protocol in the network manager's protocol stack.

        Returns:
            ResourceReservationProtocol: the resource reservation protocol in the network manager's protocol stack
        """
        for protocol in self.protocol_stack:
            if isinstance(protocol, ResourceReservationProtocol):
                return protocol
        raise ValueError("No resource reservation protocol found in the network manager's protocol stack")

    def set_routing_protocol(self, routing_protocol: Protocol) -> None:
        """Method to set the routing protocol in the network manager.

        Args:
            routing_protocol (Protocol): the routing protocol to set
        """
        self.routing_protocol = routing_protocol

    def get_forwarding_protocol(self) -> ForwardingProtocol:
        """Method to get the instance of the forwarding protocol in the network manager's protocol stack."""
        for protocol in self.protocol_stack:
            if isinstance(protocol, ForwardingProtocol):
                return protocol
        raise ValueError("No forwarding protocol found in the network manager's protocol stack")

    def get_routing_protocol(self) -> Protocol:
        """Method to get the routing protocol in the network manager.

        Returns:
            Protocol: the routing protocol in the network manager
        """
        assert self.routing_protocol is not None, "Routing protocol is not set in the network manager"
        return self.routing_protocol


def NewNetworkManager(owner: "QuantumRouter", memory_array_name: str, component_templates: dict|None=None):
    """Function to create a new network manager.

    Will create a network manager with the default protocol stack.
    This stack includes a reservation and routing protocol.

    Args:
        owner (QuantumRouter): node to attach network manager to.
        memory_array_name (str): name of the memory array component on an owner.
        component_templates:

    Returns:
        NetworkManager: a network manager object created.
    """
    if component_templates is None:
        component_templates = {}

    nm_type: str = component_templates.get('network_manager_type', 'default')

    if nm_type == 'default':
        manager = NetworkManager.create('default', owner, [])

        # Set up routing protocol
        routing: str = component_templates.get("routing", "static")
        match routing:
            case "static":
                routing_protocol_cls = StaticRoutingProtocol
            case "distributed":
                routing_protocol_cls = DistributedRoutingProtocol
            case _:
                raise NotImplementedError(f"Routing protocol {routing} not implemented.")
        routing_cls = routing_protocol_cls(owner, f"{routing_protocol_cls.__name__}")
        manager.set_routing_protocol(routing_cls)

        # Set up Forwarding Protocol
        forwarding_protocol = ForwardingProtocol(owner, owner.name + ".ForwardingProtocol")

        # Set up RSVP Protocol
        rsvp = ResourceReservationProtocol(owner, owner.name + ".RSVP", memory_array_name)
        rsvp.set_swapping_success_rate(0.5)
        forwarding_protocol.upper_protocols.append(rsvp)
        rsvp.lower_protocols.append(forwarding_protocol)
        manager.load_stack([forwarding_protocol, rsvp])
        return manager

    return NetworkManager.create(nm_type, owner)
