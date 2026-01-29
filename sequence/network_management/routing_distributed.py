"""Definition of Distributed Routing protocol.

This module defines the DistributedRoutingProtocol, which is a OSPF-like routing protocol for quantum networks
Also included is the message type used by the routing protocol.
"""


from enum import Enum, auto
from typing import TYPE_CHECKING, Union
from dataclasses import dataclass, field
from collections import defaultdict
from heapq import heappop, heappush

if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter

from ..kernel.timeline import Timeline
from ..kernel.event import Event
from ..kernel.process import Process
from ..message import Message
from ..protocol import Protocol
from ..utils import log
from ..constants import SECOND, EPSILON

MAX_AGE = 1000 * SECOND  # maximum age of LSA in seconds


class DistRoutingMsgType(Enum):
    """Enum class for message types used in distributed routing protocol."""
    HELLO = auto() # HELLO message
    DBD = auto()   # DATA BASE DESCRIPTION
    LSR = auto()   # LINK STATE REQUEST
    LSU = auto()   # LINK STATE UPDATE
    LSAck = auto() # LINK STATE ACKNOWLEDGEMENT


@dataclass(frozen=True)
class LSAHeader:
    """Link State Advertisement header.
    
    Attributes:
        advertising_router (str): who originated the LSA, "this node".
        seq_number (int): sequence number of the LSA.
        originated_time (int): time when LSA was originated.
    """
    advertising_router: str
    seq_number: int
    originated_time: int


@dataclass(frozen=True)
class Link:
    """Link information.
    
    Attributes:
        neighbor (str): neighbor node
        cost (float): cost to neighbor
    """
    neighbor: str
    cost: float


@dataclass(frozen=True)
class LSA:
    """Link State Advertisement. LS: who my neighbors are
    
    Attributes:
        header (LSAHeader): LSA header.
        links (list[Link]): list of links in this LSA.
    """
    header: LSAHeader
    links: list[Link]


@dataclass(frozen=True)
class HelloPayload:
    """HELLO payload.
    
    Attributes:
        sender (str): name of sender node.
        seen_neighbors (set[str]): set of neighbors seen by sender.
    """
    sender: str
    seen_neighbors: set[str]


@dataclass(frozen=True)
class DBDPayload:
    """Database Description payload.
    
    Attributes:
        sender (str): name of sender node.
        summaries (list[LSAHeader]): list of LSA headers summarizing LSDB.
    """
    sender: str
    summaries: list[LSAHeader]


@dataclass(frozen=True)
class LSRPayload:
    """Link State Request payload.
    
    Attributes:
        sender (str): name of sender node.
        requested (list[str]): list of advertising routers whose LSAs are requested.
    """
    sender: str
    requested: list[str]


@dataclass(frozen=True)
class LSUPayload:
    """Link State Update payload.
    
    Attributes:
        sender (str): name of sender node.
        lsas (list[LSA]): list of LSAs being sent.
    """
    sender: str
    lsas: list[LSA]


@dataclass(frozen=True)
class LSAckPayload:
    """Link State Acknowledgement payload.
    
    Attributes:
        sender (str): name of sender node.
        acks (list[tuple[str, int]]): list of (advertising_router, seq_number) acknowledgements.
    """
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

    Attributes:
        STATES (list[str]): Ordered OSPF neighbor states:
            - Down: no recent HELLOs seen
            - Init: HELLO seen from neighbor
            - TwoWay: mutual HELLOs (adjacency established)
            - ExStart: master/slave chosen, start DBD exchange
            - Exchange: DBD exchange in progress
            - Loading: requesting missing LSAs
            - Full: missing LSA all received, LSDBs synchronized
        state (str): the current state
        last_hello_received (int): time of last hello received
        pending_requested (set[str]): which LSAs are requested but not yet received
        master (bool): whether this node is master in DBD exchange
    """
    STATES = ["Down", "Init", "TwoWay", "ExStart", "Exchange", "Loading", "Full"] # there are 7 states in total
    state: str = "Down"
    last_hello_received: int = -1
    pending_requested: set[str] = field(default_factory=set)
    master: bool = False


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

    def install(self, lsa: LSA, now: int) -> bool:
        """Install LSA into database.

        Args:
            lsa (LSA): LSA to be installed.
            now (int): current simulation time (picoseconds).

        Returns:
            bool: True if LSA is new or updated, False otherwise.
        """
        adv = lsa.header.advertising_router
        existing_lsa = self.lsas.get(adv, None)
        lsa_age = now - lsa.header.originated_time

        # treat withdrawals specially: install (to enable flood) then remove later via purge
        if lsa_age >= DistributedRoutingProtocol.MAX_AGE:
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
                existing_age = now - existing_lsa.header.originated_time
                if lsa_age < existing_age:
                    self.lsas[adv] = lsa
                    return True
                else:
                    return False
            else: # lsa.header.seq_number < existing_lsa.header.seq_number:
                return False
    
    def purge_withdrawn(self, now: int) -> list[str]:
        """Purge withdrawn LSAs from database.

        Returns:
            list[str]: list of advertising routers whose LSAs are purged.
        """
        to_purge = [adv for adv, lsa in self.lsas.items() if now - lsa.header.originated_time >= DistributedRoutingProtocol.MAX_AGE]
        for adv in to_purge:
            del self.lsas[adv]
        return to_purge


class DistributedRoutingProtocol(Protocol):
    """Class to implement distributed routing protocol (OSPF-like protocol).

    Attributes: 
        owner (Node): node that protocol instance is attached to.
        name (str): label for protocol instance.
        lsdb (LinkStateDB): link state database.
        fsm (dict[str, NeighborFSM]): mapping of neighbor name to its FSM.
        link_cost (dict[str, float]): mapping of neighbor name to link cost.
        adj_cost (dict[str, float]): mapping of neighbor name with 2-way hellos to link cost.
        seq_number (int): sequence number for own LSA.
        refresh_enabled (bool): whether refreshing own LSA is enabled.
        last_originated_time (int): time of last originated LSA.
    """
    HELLO_INTERVAL = 1 * SECOND  # interval between HELLOs
    DEAD_INTERVAL  = 4 * SECOND  # time to declare neighbor dead
    MAX_AGE = 1000 * SECOND      # maximum age of LSA

    def __init__(self, owner: "QuantumRouter", name: str):
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.lsdb = LinkStateDB()
        self.fsm: dict[str, NeighborFSM] = {}
        self.link_cost: dict[str, float] = {}
        self.adj_cost: dict[str, float] = {}
        self.seq_number = 0
        self.refresh_enabled = True
        self.last_originated_time = -1

    def init(self):
        """Initialize:
           1) the FSM for each neighbor
           2) the first hello event
           3) the first LSA refresh event (enabled by default)
        """
        # init the FSM for each neighbor
        for neighbor_name in self.link_cost.keys():
            self.ensure_fsm(neighbor_name)
        # schedule the first hello
        self.send_hello(delay=self.HELLO_INTERVAL)
        # schedule the first LSA refresh if enabled
        if self.refresh_enabled:
            process = Process(self, "refresh_lsa", [self.MAX_AGE // 2])
            time = self.owner.timeline.now() + self.MAX_AGE // 2
            event = Event(time, process)
            self.owner.timeline.schedule(event)

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
        log.logger.debug(f"{self.owner.name}: Received {msg} from {src}")
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

    def refresh_lsa(self, delay: int):
        """Refresh own LSA now via flooding, then schedule the next refresh after delay.

        Args:
            delay (int): the delay (picoseconds) for sending the next refresh event.
        """
        if not self.refresh_enabled:
            return
        self.originate_and_flood()
        process = Process(self, "refresh_lsa", [self.MAX_AGE // 2])
        time = self.owner.timeline.now() + delay
        event = Event(time, process)
        self.owner.timeline.schedule(event)

    def expire_lsa(self, last_originated_time: int):
        """Withdraw own LSA when it reaches max_age (if refresh is disabled).

        Args:
            last_originated_time (int): the previous origin time of the LSA.
        """
        if self.refresh_enabled:
            return
        if last_originated_time != self.last_originated_time:
            return
        now = self.owner.timeline.now()
        if now - last_originated_time < self.MAX_AGE:
            process = Process(self, "expire_lsa", [last_originated_time])
            time = last_originated_time + self.MAX_AGE
            event = Event(time, process)
            self.owner.timeline.schedule(event)
            return
        withdrawal = self.originate_withdrawal()
        updated = self.lsdb.install(withdrawal, now)
        if updated:
            forwarding_table = self.run_spf()
            self.owner.network_manager.set_forwarding_table(forwarding_table)
        self.flood_to_all_neighbors(withdrawal)
        self.lsdb.purge_withdrawn(now)

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
        elif fsm.state == "Down":
            if neighbor in self.adj_cost:
                del self.adj_cost[neighbor]
                self.originate_and_flood()

    def start_exstart(self, neighbor: str):
        """Start ExStart state with neighbor.
           A master node is elected and begin DBD exchange.

        Args:
            neighbor (str): name of neighbor.
        """
        fsm = self.ensure_fsm(neighbor)
        fsm.pending_requested.clear()
        fsm.master = self.owner.name > neighbor # let the node with bigger name be the master
        self.set_state(neighbor, "ExStart")
        if fsm.master:
            self.send_dbd(neighbor)

    def send_dbd(self, neighbor: str):
        """Send DBD message to neighbor.

        Args:
            neighbor (str): name of neighbor.
        """
        summaries = []
        for lsa in self.lsdb:
            if self.get_age(lsa) < self.MAX_AGE:
                summaries.append(lsa.header)
        dbd_payload = DBDPayload(sender=self.owner.name, summaries=summaries)
        dbd_msg = DistRoutingMessage(DistRoutingMsgType.DBD, receiver="DistributedRoutingProtocol", payload=dbd_payload)
        self.owner.send_message(neighbor, dbd_msg)

    def originate_and_flood(self):
        """Originate own LSA and flood to all neighbors with 2-way adjacency.
        """
        lsa = self.originate()
        # install into own LSDB (always newer for self-originated LSA)
        updated = self.lsdb.install(lsa, self.owner.timeline.now())
        if updated:
            forwarding_table = self.run_spf()  # recompute routes
            self.owner.network_manager.set_forwarding_table(forwarding_table)
        self.flood_to_all_neighbors(lsa)
    
    def originate(self) -> LSA:
        """Originate and return its LSA, meanwhile increment its sequence number.

        Return:
            LSA: the originated LSA.
        """
        links = []
        for neighbor, cost in sorted(self.adj_cost.items()):
            links.append(Link(neighbor=neighbor, cost=cost))
        now = self.owner.timeline.now()
        header = LSAHeader(advertising_router=self.owner.name, seq_number=self.seq_number, originated_time=now)
        lsa = LSA(header=header, links=links)
        self.seq_number += 1
        self.last_originated_time = now
        if not self.refresh_enabled:
            process = Process(self, "expire_lsa", [self.last_originated_time])
            time = self.last_originated_time + self.MAX_AGE
            event = Event(time, process)
            self.owner.timeline.schedule(event)
        return lsa

    def originate_withdrawal(self) -> LSA:
        """Originate a withdrawal LSA (MAX_AGE) for this router.
        """
        now = self.owner.timeline.now()
        header = LSAHeader(advertising_router=self.owner.name, seq_number=self.seq_number, originated_time=now - self.MAX_AGE)
        lsa = LSA(header=header, links=[])
        self.seq_number += 1
        return lsa

    def run_spf(self) -> dict[str, str]:
        """Run Shortest Path First (SPF) algorithm to compute routing table.

        Return:
            forwarding_table (dict[str, str]): mapping of destination to next hop.
        """
        log.logger.info(f"{self.owner.name}: Running SPF algorithm to compute routing table.")
        # step 1: build adjacency graph from LSDB
        g = defaultdict(list) # node -> list[(neighbor, cost)]
        nodes = set()
        for lsa in self.lsdb:
            if self.get_age(lsa) >= self.MAX_AGE:
                continue
            u = lsa.header.advertising_router
            nodes.add(u)
            for link in lsa.links:
                v = link.neighbor
                c = link.cost
                g[u].append((v, c))
                nodes.add(v)
        # step 2:Dijkstra's algorithm
        dist = {n: float('inf') for n in nodes}
        dist[self.owner.name] = 0
        prev = {n: set() for n in nodes}   # node -> set of previous nodes in shortest paths
        visited = set()
        queue = [(0, self.owner.name)]        # (cost, node)
        while queue:
            d, u = heappop(queue)
            if u not in visited:
                visited.add(u)
                for v, cost in g[u]:
                    if v in visited:
                        continue
                    alt = d + cost
                    if alt < dist[v]:                  # a shorter alternative path to v via u
                        dist[v] = alt
                        prev[v] = {u}
                        heappush(queue, (alt, v))
                    elif abs(alt - dist[v]) < EPSILON: # multiple shortest paths
                        prev[v].add(u)
        # step 3: build forwarding table
        forwarding_table = {} # dst -> next hop
        for dst in nodes:
            if dst == self.owner.name or dist[dst] == float('inf'):
                continue
            candidates = set()
            cur_nodes = [dst]
            while cur_nodes and len(candidates) == 0: # backtrack until reaching neighbors, just need one candidate
                next_cur_nodes = []
                for cur in cur_nodes:
                    for p in prev[cur]:
                        if p == self.owner.name:
                            candidates.add(cur)
                        else:
                            next_cur_nodes.append(p)
                cur_nodes = next_cur_nodes
            if candidates:
                forwarding_table[dst] = min(candidates) # choose the lexicographically smallest next hop
        log.logger.info(f"{self.owner.name}: Computed routing table: dist={dist}, forwarding_table={forwarding_table}")
        return forwarding_table

    def get_age(self, item: LSA | LSAHeader) -> int:
        """Get age of LSA or LSAHeader.

        Args:
            item (LSA | LSAHeader): LSA or LSAHeader.
        Returns:
            int: age of the item in picoseconds.
        """
        if isinstance(item, LSA):
            return self.owner.timeline.now() - item.header.originated_time
        elif isinstance(item, LSAHeader):
            return self.owner.timeline.now() - item.originated_time
        else:
            raise ValueError("item must be LSA or LSAHeader")

    def update_forwarding_rule(self, dst: str, next_node: str):
        """updates dst to map to next_node in forwarding table.
           If dst not in forwarding table, add new rule.

        Args:
            dst (str): name of destination node.
            next_node (str): name of next hop node.
        """
        forwarding_table = self.owner.network_manager.get_forwarding_table()
        forwarding_table[dst] = next_node

    def flood_to_all_neighbors(self, lsa: LSA, exclude_neighbor: str | None = None):
        """Flood LSA to all neighbors with 2-way adjacency.
           An LSU message containing the LSA is sent to each neighbor, except the excluded neighbor if specified.

        Args:
            lsa (LSA): LSA to be flooded.
            exclude_neighbor (str | None): neighbor to exclude from flooding.
        """
        log.logger.debug(f"{self.owner.name}: Flooding {lsa} to neighbors {list(self.adj_cost.keys())}, excluding {exclude_neighbor}")
        for neighbor in self.adj_cost.keys():
            if neighbor == exclude_neighbor:
                continue
            lsu_payload = LSUPayload(sender=self.owner.name, lsas=[lsa])
            lsu_msg = DistRoutingMessage(DistRoutingMsgType.LSU, receiver="DistributedRoutingProtocol", payload=lsu_payload)
            self.owner.send_message(neighbor, lsu_msg)

    def handle_dbd(self, src: str, payload: DBDPayload):
        """Handle DBD message from neighbor.
           Request any missing or outdated LSAs.

        Args:
            src (str): name of source node.
            payload (DBDPayload): payload of DBD message.
        """
        fsm = self.ensure_fsm(src)
        if fsm.state == "Down":
            log.logger.warning(f"{self.owner.name}: Received DBD from {src} in Down state, ignoring.")
            return
        if fsm.state == "TwoWay":
            # ensure master/slave roles are set and transition to ExStart
            self.start_exstart(src)
            fsm = self.ensure_fsm(src)  # re-fetch fsm after state change
        if fsm.state == "ExStart":
            if fsm.master is False:
                # slave sees DBD from master, transition to Exchange
                self.set_state(src, "Exchange")
                self.send_dbd(src)
            else:
                # master sees DBD from slave, transition to Exchange
                self.set_state(src, "Exchange")
        # get the list of LSAs to request
        requested = []
        for lsa_header in payload.summaries:
            existing_lsa = self.lsdb.get(lsa_header.advertising_router)
            if existing_lsa is None:
                requested.append(lsa_header.advertising_router) # missing LSA: neighbor has LSA, but we don't have
            else:
                if lsa_header.seq_number > existing_lsa.header.seq_number:
                    requested.append(lsa_header.advertising_router)
                if lsa_header.seq_number == existing_lsa.header.seq_number and self.get_age(lsa_header) < self.get_age(existing_lsa):
                    requested.append(lsa_header.advertising_router)
        if requested:
            # ask for the requested LSAs
            fsm.pending_requested = set(requested)
            self.set_state(src, "Loading")
            lsr_payload = LSRPayload(sender=self.owner.name, requested=requested)
            lsr_msg = DistRoutingMessage(DistRoutingMsgType.LSR, receiver="DistributedRoutingProtocol", payload=lsr_payload)
            self.owner.send_message(src, lsr_msg)
        else:
            # clear the pending requested LSAs advance the neighbor to Full state because DBs are in sync
            if fsm.pending_requested:
                fsm.pending_requested.clear()
            if fsm.state != "Full":
                self.set_state(src, "Full")

    def handle_lsr(self, src: str, payload: LSRPayload):
        """Handle LSR message from neighbor. Send back the requested LSAs.

        Args:
            src (str): name of source node.
            payload (LSRPayload): payload of LSR message.
        """
        fsm = self.ensure_fsm(src)
        if fsm.state not in ["Exchange", "Loading", "Full"]:
            log.logger.warning(f"{self.owner.name}: Received LSR from {src} in state {fsm.state}, ignoring.")
            return
        lsas_to_send = []
        for adv in payload.requested:
            lsa = self.lsdb.get(adv)
            if lsa is not None:
                lsas_to_send.append(lsa)
        if lsas_to_send:
            lsu_payload = LSUPayload(sender=self.owner.name, lsas=lsas_to_send)
            lsu_msg = DistRoutingMessage(DistRoutingMsgType.LSU, receiver="DistributedRoutingProtocol", payload=lsu_payload)
            self.owner.send_message(src, lsu_msg)

    def handle_lsu(self, src: str, payload: LSUPayload):
        """Handle LSU message from neighbor.

        Args:
            src (str): name of source node.
            payload (LSUPayload): payload of LSU message.
        """
        fsm_src = self.ensure_fsm(src)
        if fsm_src.state not in ["Exchange", "Loading", "Full"]:
            log.logger.warning(f"{self.owner.name}: Received LSU from {src} in state {fsm_src.state}, ignoring.")
            return
        acks = []
        lsdb_updated = False
        for lsa in payload.lsas:            
            updated = self.lsdb.install(lsa, self.owner.timeline.now())
            if updated is True:
                lsdb_updated = True
                acks.append((lsa.header.advertising_router, lsa.header.seq_number))
                if self.get_age(lsa) < self.MAX_AGE:
                    # flood to other neighbors except the one it came from
                    self.flood_to_all_neighbors(lsa, exclude_neighbor=src)
                else:
                    # still flood, then purge withdrawn LSA from own LSDB
                    self.flood_to_all_neighbors(lsa, exclude_neighbor=src)
                self.lsdb.purge_withdrawn(self.owner.timeline.now())
                # remove from pending_requested of the lsa.header.advertising_router's (not necessarry src's) FSM
                fsm_adv_router = self.ensure_fsm(lsa.header.advertising_router)
                if fsm_adv_router.state == "Loading" and lsa.header.advertising_router in fsm_adv_router.pending_requested:
                    fsm_adv_router.pending_requested.remove(lsa.header.advertising_router)
                    if len(fsm_adv_router.pending_requested) == 0:
                        self.set_state(lsa.header.advertising_router, "Full")
        if lsdb_updated:    # recompute routes if LSDB is updated
            forwarding_table = self.run_spf()
            self.owner.network_manager.set_forwarding_table(forwarding_table)
        if acks:            # send LSAck back to sender
            lsack_payload = LSAckPayload(sender=self.owner.name, acks=acks)
            lsack_msg = DistRoutingMessage(DistRoutingMsgType.LSAck, receiver="DistributedRoutingProtocol", payload=lsack_payload)
            self.owner.send_message(src, lsack_msg)
        # if no more pending requested LSAs, transition to Full state
        if fsm_src.state == "Loading" and len(fsm_src.pending_requested) == 0:
            self.set_state(src, "Full")

    def handle_lsack(self, src: str, payload: LSAckPayload):
        """Handle LSAck message from neighbor.

        Args:
            src (str): name of source node.
            payload (LSAckPayload): payload of LSAck message.
        """
        log.logger.info(f"{self.owner.name}: Received LSAck from {src}: {payload.acks}. Do nothing for now.")
