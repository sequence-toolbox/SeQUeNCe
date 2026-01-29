"""Definition of the Network Manager.

This module defines the NetworkManager class, an implementation of the SeQUeNCe network management module.
Also included in this module is the message type used by the network manager and a function for generating network managers with default protocols.
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..protocol import StackProtocol

from ..message import Message
from ..protocol import Protocol
from .routing_distributed import DistributedRoutingProtocol
from .routing_static import StaticRoutingProtocol
from .forwarding import ForwardingProtocol
from .reservation import ResourceReservationProtocol, ResourceReservationMessage, RSVPMsgType
from ..utils import log


class NetworkManagerMessage(Message):
    """Message used by the network manager.

    Attributes:
        msg_type (Enum): message type required by base message type.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be passed through destination network manager.
    """

    def __init__(self, msg_type: Enum, receiver: str, payload: "Message"):
        super().__init__(msg_type, receiver)
        self.payload = payload

    def __str__(self) -> str:
        return f"type={self.msg_type}; receiver={self.receiver}; payload={self.payload}"


class NetworkManager:
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

    def __init__(self, owner: "QuantumRouter", protocol_stack: "list[StackProtocol]"):
        """Constructor for network manager.

        Args:
            owner (QuantumRouter): node network manager is attached to.
            protocol_stack (list[StackProtocol]): stack of protocols to use for processing.
        """

        log.logger.info(f"Create network manager of Node {owner.name}")
        self.name = "network_manager"
        self.owner = owner
        self.protocol_stack = protocol_stack
        self.load_stack(protocol_stack)
        self.forwarding_table = {}
        self.routing_protocol = None

    def load_stack(self, stack: "list[StackProtocol]"):
        """Method to load a defined protocol stack.

        Args:
            stack (list[StackProtocol]): new protocol stack.
        """

        self.protocol_stack = stack
        if len(self.protocol_stack) > 0:
            self.protocol_stack[0].lower_protocols.append(self)
            self.protocol_stack[-1].upper_protocols.append(self)

    def push(self, **kwargs):
        """Method to receive pushes from lowest protocol in protocol stack.

        Will create message to send to another node.

        Keyword Args:
            msg (any): message to deliver.
            dst (str): name of destination node.
        """

        message = NetworkManagerMessage(Enum, "network_manager", kwargs["msg"])
        self.owner.send_message(kwargs["dst"], message)

    def pop(self, **kwargs):
        """Method to receive pops from highest protocol in protocol stack.

        Will get reservation from message and attempt to meet it.

        Keyword Args:
            msg (any): message containing reservation.
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

    def received_message(self, src: str, msg: "NetworkManagerMessage"):
        """Method to receive transmitted network reservation method.

        Will pop message to lowest protocol in protocol stack.

        Args:
            src (str): name of source node for message.
            msg (NetworkManagerMessage): message received.

        Side Effects:
            Will invoke `pop` method of 0 indexed protocol in `protocol_stack`.
        """

        log.logger.info(f"{self.owner.name} network manager receives message from {src}: {msg}")
        self.protocol_stack[0].pop(src=src, msg=msg.payload)

    def request(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float,
                entanglement_number: int = 1, identity: int = 0) -> None:
        """Method to make an entanglement request.

        Will defer request to top protocol in protocol stack.

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

        self.protocol_stack[-1].push(responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity)

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

    def get_routing_protocol(self) -> Protocol:
        """Method to get the routing protocol in the network manager.

        Returns:
            Protocol: the routing protocol in the network manager
        """
        return self.routing_protocol


def NewNetworkManager(owner: "QuantumRouter", memory_array_name: str, component_templates: dict = {}) -> "NetworkManager":
    """Function to create a new network manager.

    Will create a network manager with default protocol stack.
    This stack inclused a reservation and routing protocol.

    Args:
        owner (QuantumRouter): node to attach network manager to.
        memory_array_name (str): name of the memory array component on owner.
        routing_protocol_cls (type[Protocol]): routing protocol class to use for control plane.

    Returns:
        NetworkManager: network manager object created.
    """
    swapping_success_rate = 0.5
    manager = NetworkManager(owner, [])
    routing = component_templates.get("routing", "static")
    match routing:
        case "static":
            routing_protocol_cls = StaticRoutingProtocol
        case "distributed":
            routing_protocol_cls = DistributedRoutingProtocol
        case _:
            raise NotImplementedError(f"Routing protocol {routing} not implemented.")   
    routing = routing_protocol_cls(owner, f"{routing_protocol_cls.__name__}")
    manager.set_routing_protocol(routing)
    forwarding_protocol = ForwardingProtocol(owner, owner.name + ".ForwardingProtocol")
    rsvp = ResourceReservationProtocol(owner, owner.name + ".RSVP", memory_array_name)
    rsvp.set_swapping_success_rate(swapping_success_rate)
    forwarding_protocol.upper_protocols.append(rsvp)
    rsvp.lower_protocols.append(forwarding_protocol)
    manager.load_stack([forwarding_protocol, rsvp])
    return manager
