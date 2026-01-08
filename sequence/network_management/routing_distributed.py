"""Definition of Distributed Routing protocol.

This module defines the DistributedRoutingProtocol, which is a OSPF-like routing protocol for quantum networks
Also included is the message type used by the routing protocol.
"""


from enum import Enum, auto
from typing import TYPE_CHECKING, Union
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..topology.node import Node

from ..message import Message
from ..protocol import Protocol
from ..utils import log


class DistRoutingMsgType(Enum):
    """Enum class for message types used in distributed routing protocol."""
    HELLO = auto() # HELLO message
    DBD = auto()   # DATA BASE DESCRIPTION
    LSR = auto()   # LINK STATE REQUEST
    LSU = auto()   # LINK STATE UPDATE
    LSA = auto()   # LINK STATE ACKNOWLEDGEMENT


@dataclass(frozen=True)
class LSAHeader:
    """Link State Advertisement header."""
    advertising_router: str
    seq_number: int
    age: int


@dataclass(frozen=True)
class Link:
    """Link information."""
    neighbor: str
    cost: float


@dataclass(frozen=True)
class LSA:
    """Link State Advertisement."""
    header: LSAHeader
    links: list[Link]


@dataclass(frozen=True)
class HelloPayload:
    sender: str
    seen_neighbors: set[str]


@dataclass(frozen=True)
class DBDPayload:
    """Database Description payload."""
    sender: str
    summaries: list[LSAHeader]


@dataclass(frozen=True)
class LSRPayload:
    """Link State Request payload."""
    sender: str
    requested: list[str]


@dataclass(frozen=True)
class LSUPayload:
    """Link State Update payload."""
    sender: str
    lsas: list[LSA]


@dataclass(frozen=True)
class LSAckPayload:
    sender: str
    acks: list[tuple[str, int]]  # list of (advertising_router, seq_number)

DistRoutingPayload = Union[HelloPayload, DBDPayload, LSRPayload, LSUPayload, LSAckPayload]


class DistRoutingMessage(Message):
    """Message used by the distributed routing protocol.

    Attributes:
        msg_type (Enum): message type required by base message type.
        receiver (str): name of destination protocol instance.
        payload (DistRoutingPayload): message to be passed through destination network manager.
    """
    def __init__(self, msg_type: DistRoutingMsgType, receiver: str, payload: DistRoutingPayload):
        super().__init__(msg_type, receiver)
        self.payload = payload




class DistributedRoutingProtocol(Protocol):
    """Class to implement distributed routing protocol (OSPF-like protocol).

    Attributes: 
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
    """
    def __init__(self, owner: "Node", name: str):
        super().__init__(owner, name)

    def received_message(self, src: str, msg):
        pass

