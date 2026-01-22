"""Definition of Distributed Routing protocol.

This module defines the DistributedRoutingProtocol, which is a OSPF-like routing protocol for quantum networks
Also included is the message type used by the routing protocol.
"""


from enum import Enum, auto
from typing import TYPE_CHECKING, Union
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter

from ..kernel.timeline import Timeline
from ..kernel.event import Event
from ..kernel.process import Process
from ..message import Message
from ..protocol import Protocol
from ..utils import log
from ..constants import SECOND

MAX_AGE = 1000  # maximum age of LSA in seconds

class DistRoutingMsgType(Enum):
    """Enum class for message types used in distributed routing protocol."""
    HELLO = auto() # HELLO message
    DBD = auto()   # DATA BASE DESCRIPTION
    LSR = auto()   # LINK STATE REQUEST
    LSU = auto()   # LINK STATE UPDATE
    LSAck = auto() # LINK STATE ACKNOWLEDGEMENT


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
    """Link State Advertisement. LS: who my neighbors are, cost to each."""
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

    def __str__(self) -> str:
        return f"DistRoutingMessage(payload={self.payload})"


@dataclass
class NeighborFSM:
    """Finite State Machine for each neighbors.
    """
    STATES = ["Down", "Init", "TwoWay", "ExStart", "Exchange", "Loading", "Full"] # there are 7 states in total
    state: str = "Down"
    last_hello_received: int = -1  # time of last hello received
    pending_requested: set[str] = field(default_factory=set)


class LinkStateDB:
    """Link State Database for distributed routing protocol.

    Attributes:
        lsas (dict[str, LSA]): mapping of advertising router to LSA.
    """
    def __init__(self):
        self.lsas: dict[str, LSA] = {}
    
    def get(self, adv: str) -> LSA | None:
        return self.lsas.get(adv, None)
    
    def __iter__(self) -> iter:
        return iter(self.lsas.values())

    def install(self, lsa: LSA) -> bool:
        """Install LSA into database.

        Args:
            lsa (LSA): LSA to be installed.

        Returns:
            bool: True if LSA is new or updated, False otherwise.
        """
        adv = lsa.header.advertising_router
        existing_lsa = self.lsas.get(adv, None)

        # treat withdrawals specially: install (to enable flood) then remove
        if lsa.header.age >= MAX_AGE:
            if existing_lsa is not None:
                self.lsas[lsa.header.advertising_router] = lsa
                return True
            return False

        if existing_lsa is None:
            self.lsas[adv] = lsa
            return True
        else:
            # install if newer
            if lsa.header.seq_number > existing_lsa.header.seq_number:
                self.lsas[adv] = lsa
                return True
            elif lsa.header.seq_number == existing_lsa.header.seq_number:
                if lsa.header.age < existing_lsa.header.age:
                    self.lsas[adv] = lsa
                    return True
            else: # lsa.header.seq_number < existing_lsa.header.seq_number:
                return False
    
    def purge_withdrawn(self) -> list[str]:
        """Purge withdrawn LSAs from database.

        Returns:
            list[str]: list of advertising routers whose LSAs are purged.
        """
        to_purge = [adv for adv, lsa in self.lsas.items() if lsa.header.age >= MAX_AGE]
        for adv in to_purge:
            del self.lsas[adv]
        return to_purge


class DistributedRoutingProtocol(Protocol):
    """Class to implement distributed routing protocol (OSPF-like protocol).

    Attributes: 
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
    """
    HELLO_INTERVAL = 1 * SECOND  # interval between HELLOs
    DEAD_INTERVAL  = 4 * SECOND  # time to declare neighbor dead

    def __init__(self, owner: "QuantumRouter", name: str):
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.lsdb = LinkStateDB()              # link state database
        self.fsm: dict[str, NeighborFSM] = {}  # neighbor name to FSM
        self.link_cost: dict[str, float] = {}  # neighbor to link cost
        self.adj_cost: dict[str, float] = {}   # neighbor with 2-way hellos to link cost
        self.seq_number = 1                    # sequence number for own LSA

    def init(self):
        """Initialize
        """
        # init the FSM for each neighbor
        for neighbor_name in self.link_cost.keys():
            self.ensure_fsm(neighbor_name)

        # schedule the first hello
        self.send_hello(delay=self.HELLO_INTERVAL)

    def ensure_fsm(self, neighbor: str) -> NeighborFSM:
        """Ensure FSM exists for neighbor.

        Args:
            neighbor (str): name of neighbor.

        Returns:
            NeighborFSM: FSM for neighbor.
        """
        if neighbor not in self.fsm:
            self.fsm[neighbor] = NeighborFSM()
        return self.fsm[neighbor]

    def received_message(self, src: str, msg):
        """Receive Distributed Routing message from another node.
        
        Args:
            src (str): name of source node.
            msg (Message): message received.
        """
        log.logger.debug(f"{self.owner.name}: Received {msg.msg_type} from {src}")
        msg_type = msg.msg_type

        match msg_type:
            case DistRoutingMsgType.HELLO:
                self.handle_hello(src, msg.payload)
            case DistRoutingMsgType.DBD:
                self.handle_dbd(src, msg.payload)
            case DistRoutingMsgType.LSR:
                self.handle_lsr(src, msg.payload)
            case DistRoutingMsgType.LSU:
                self.handle_lsu(src, msg.payload)
            case DistRoutingMsgType.LSAck:
                self.handle_lsack(src, msg.payload)
            case _:
                log.logger.error(f"{self.owner.name}: Unknown message type {msg_type} received from {src}")

    def send_hello(self, delay: int):
        """Send HELLO message to all neighbors now,
           and schedule the next send_hello after delay (picoseconds).

        Args:
            delay (int): the delay (picoseconds) for sending the next send_hello event.
        """
        # send hello to all neighbors
        for neighbor in self.link_cost.keys():
            seen_neighbors = {n for n, fsm in self.fsm.items() if fsm.state != "Down"}
            hello_payload = HelloPayload(sender=self.owner.name, seen_neighbors=seen_neighbors)
            hello_msg = DistRoutingMessage(DistRoutingMsgType.HELLO, receiver="DistributedRoutingProtocol", payload=hello_payload)
            self.owner.send_message(neighbor, hello_msg)
        
        process = Process(self, "send_hello", [self.HELLO_INTERVAL])
        time = self.owner.timeline.now() + delay
        event = Event(time, process)
        self.owner.timeline.schedule(event)

    def handle_hello(self, src: str, payload: HelloPayload):
        """Handle HELLO message from neighbor.

        Args:
            src (str): name of source node.
            payload (HelloPayload): payload of HELLO message.
        """
        fsm = self.ensure_fsm(src)
        fsm.last_hello_received = self.owner.timeline.now()
        # schedule an event after DEAD_INTERVAL to check for neighbor liveness
        process = Process(self, "check_neighbor_liveness", [src, fsm.last_hello_received])
        time = self.owner.timeline.now() + self.DEAD_INTERVAL
        event = Event(time, process)
        self.owner.timeline.schedule(event)
        # update FSM state
        if fsm.state == "Down":
            self.set_state(src, "Init")
        two_way = self.owner.name in payload.seen_neighbors
        if two_way and fsm.state == "Init":
            self.set_state(src, "TwoWay")
            self.start_exstart(src)

    def check_neighbor_liveness(self, neighbor: str, last_hello_time: int):
        """Check if neighbor is still alive.

        Args:
            neighbor (str): name of neighbor.
            last_hello_time (int): time of last hello received from neighbor.
        """
        fsm = self.ensure_fsm(neighbor)
        if fsm.last_hello_received == last_hello_time:
            # no hello received since last check, declare neighbor down
            self.set_state(neighbor, "Down")

    def set_state(self, neighbor: str, new_state: str):
        """Set the state of the neighbor FSM.

        Args:
            neighbor (str): name of neighbor.
            new_state (str): new state to set.
        """
        fsm = self.ensure_fsm(neighbor)
        if fsm.state == new_state: # no change in state
            return
        log.logger.info(f"{self.owner.name}: Neighbor {neighbor} state change: {fsm.state} -> {new_state}")
        fsm.state = new_state      # change in state
        if fsm.state == "TwoWay":
            self.adj_cost[neighbor] = self.link_cost[neighbor]
            self.originate_and_flood()
        else:
            if neighbor in self.adj_cost:
                del self.adj_cost[neighbor]
                self.originate_and_flood()

    def start_exstart(self, neighbor: str):
        """Start ExStart state with neighbor.

        Args:
            neighbor (str): name of neighbor.
        """
        pass

    def originate_and_flood(self):
        """Originate own LSA and flood to all neighbors with 2-way adjacency.
        """
        pass

    def handle_dbd(self, src: str, payload: DBDPayload):
        """Handle DBD message from neighbor.

        Args:
            src (str): name of source node.
            payload (DBDPayload): payload of DBD message.
        """
        pass

    def handle_lsr(self, src: str, payload: LSRPayload):
        """Handle LSR message from neighbor.

        Args:
            src (str): name of source node.
            payload (LSRPayload): payload of LSR message.
        """
        pass

    def handle_lsu(self, src: str, payload: LSUPayload):
        """Handle LSU message from neighbor.

        Args:
            src (str): name of source node.
            payload (LSUPayload): payload of LSU message.
        """
        pass

    def handle_lsack(self, src: str, payload: LSAckPayload):
        """Handle LSAck message from neighbor.

        Args:
            src (str): name of source node.
            payload (LSAAckPayload): payload of LSAck message.
        """
        pass