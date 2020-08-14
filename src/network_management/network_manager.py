"""Definition of the Network Manager.

This module defines the NetworkManager class, an implementation of the SeQUeNCe network management module.
Also included in this module is the message type used by the network manager and a function for generating network managers with default protocols.
"""

from enum import Enum
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..protocol import StackProtocol

from ..message import Message
from .routing import StaticRoutingProtocol
from .reservation import ResourceReservationProtocol, ResourceReservationMessage, RSVPMsgType


class NetworkManagerMessage(Message):
    """Message used by the network manager.

    Attributes:
        message_type (Enum): message type required by base message type.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be passed through destination network manager.
    """

    def __init__(self, msg_type: Enum, receiver: str, payload: "Message"):
        Message.__init__(self, msg_type, receiver)
        self.payload = payload


class NetworkManager():
    """Network manager implementation class.

    The network manager is responsible for the operations of a node within a broader quantum network.
    This is done through a `protocol_stack` of protocols, which messages are passed and packaged through.

    Attributes:
        name (str): name of the network manager instance.
        owner (QuantumRouter): node that protocol instance is attached to.
        protocol_stack (List[StackProtocol]): network manager protocol stack.
    """

    def __init__(self, owner: "QuantumRouter", protocol_stack: "List[StackProtocol]"):
        self.name = "network_manager"
        self.owner = owner
        self.protocol_stack = protocol_stack
        self.load_stack(protocol_stack)

    def load_stack(self, stack: "List[StackProtocol]"):
        self.protocol_stack = stack
        if len(self.protocol_stack) > 0:
            self.protocol_stack[0].lower_protocols.append(self)
            self.protocol_stack[-1].upper_protocols.append(self)

    def push(self, **kwargs):
        message = NetworkManagerMessage(Enum, "network_manager", kwargs["msg"])
        self.owner.send_message(kwargs["dst"], message)

    def pop(self, **kwargs):
        msg = kwargs.get("msg")
        assert isinstance(msg, ResourceReservationMessage)
        reservation = msg.reservation
        if reservation.initiator == self.owner.name:
            if msg.msg_type == RSVPMsgType.APPROVE:
                self.owner.get_reserve_res(reservation, True)
            else:
                self.owner.get_reserve_res(reservation, False)
        elif reservation.responder == self.owner.name:
            self.owner.get_other_reservation(reservation)

    def received_message(self, src: str, msg: "NetworkManagerMessage"):
        self.protocol_stack[0].pop(src=src, msg=msg.payload)

    def request(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float) -> None:
        self.protocol_stack[-1].push(responder, start_time, end_time, memory_size, target_fidelity)


def NewNetworkManager(owner: "QuantumRouter") -> "NetworkManager":
    manager = NetworkManager(owner, [])
    routing = StaticRoutingProtocol(owner, owner.name + ".StaticRoutingProtocol", {})
    rsvp = ResourceReservationProtocol(owner, owner.name + ".RSVP")
    routing.upper_protocols.append(rsvp)
    rsvp.lower_protocols.append(routing)
    manager.load_stack([routing, rsvp])
    return manager
