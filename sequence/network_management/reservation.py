"""Definition of Reservation protocol and related tools.

This module provides a definition for the reservation protocol used by the network manager.
This includes the Reservation, MemoryTimeCard, and QCap classes, which are used by the network manager to track reservations.
Also included is the definition of the message type used by the reservation protocol.
"""

from enum import Enum, auto
from typing import List, TYPE_CHECKING, Any, Dict, Tuple

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..resource_management.memory_manager import MemoryInfo, MemoryManager
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol

from ..resource_management.rule_manager import Rule, Arguments
from ..entanglement_management.generation import EntanglementGenerationA
from ..entanglement_management.purification import BBPSSW
from ..entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from ..message import Message
from ..protocol import StackProtocol
from ..kernel.event import Event
from ..kernel.process import Process

ENTANGLED = 'ENTANGLED'
RAW = 'RAW'


class RSVPMsgType(Enum):
    """Defines possible message types for the reservation protocol."""

    REQUEST = auto()
    REJECT = auto()
    APPROVE = auto()


class ResourceReservationMessage(Message):
    """Message used by resource reservation protocol.

    This message contains all information passed between reservation protocol instances.
    Messages of different types contain different information.

    Attributes:
        msg_type (RSVPMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        reservation (Reservation): reservation object relayed between nodes.
        qcaps (List[QCaps]): cumulative quantum capacity object list (if `msg_type == REQUEST`)
        path (List[str]): cumulative node list for entanglement path (if `msg_type == APPROVE` or `msg_type == REJECT`)
    """

    def __init__(self, msg_type: any, receiver: str, reservation: "Reservation", **kwargs):
        super().__init__(msg_type, receiver)
        self.reservation = reservation
        if self.msg_type is RSVPMsgType.REQUEST:
            self.qcaps = []
        elif self.msg_type is RSVPMsgType.REJECT:
            self.path = kwargs["path"]
        elif self.msg_type is RSVPMsgType.APPROVE:
            self.path = kwargs["path"]
        else:
            raise Exception("Unknown type of message")

    def __str__(self):
        return f"|type={self.msg_type}; reservation={self.reservation}|"


# entanglement generation

def eg_rule_action1(memories_info: List["MemoryInfo"], args: Dict[str, Any]) -> Tuple[EntanglementGenerationA, List[None], List[None], List[None]]:
    """Action function used by entanglement generation protocol on nodes except the initiator, i.e., index > 0
    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid, path[index - 1], memory)
    return protocol, [None], [None], [None]


def eg_rule_action2(memories_info: List["MemoryInfo"], args: Arguments) -> Tuple[EntanglementGenerationA, List[str], List["eg_req_func"], List[Dict]]:
    """Action function used by entanglement generation protocol on nodes except the responder, i.e., index < len(path) - 1
    """
    mid = args["mid"]
    path = args["path"]
    index = args["index"]
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid, path[index + 1], memory)
    req_args = {"name": args["name"], "reservation": args["reservation"]}
    return protocol, [path[index + 1]], [eg_req_func], [req_args]


def eg_req_func(protocols: List["EntanglementProtocol"], args: Arguments) -> EntanglementGenerationA:
    """Function used by `eg_rule_action2` function for selecting generation protocols on the remote node

    Args:
        protocols: the waiting protocols (wait for request)
        args: arguments from the node who sent the request
    Return:
        the selected protocol
    """
    name = args["name"]
    reservation = args["reservation"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementGenerationA)
                and protocol.remote_node_name == name
                and protocol.rule.get_reservation() == reservation):
            return protocol


def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by entanglement generation protocol on nodes
    """
    memory_indices = args['memory_indices']
    if memory_info.state == "RAW" and memory_info.index in memory_indices:
        return [memory_info]
    else:
        return []


# entanglement purification

def ep_rule_action1(memories_info: List["MemoryInfo"], args: Arguments) -> Tuple[BBPSSW, List[str], List["ep_req_func1"], List[Dict]]:
    """Action function used by BBPSSW protocol on nodes except the responder node
    """
    memories = [info.memory for info in memories_info]
    name = "EP.%s.%s" % (memories[0].name, memories[1].name)
    protocol = BBPSSW(None, name, memories[0], memories[1])
    dsts = [memories_info[0].remote_node]
    req_funcs = [ep_req_func1]
    req_args = [{"remote0": memories_info[0].remote_memo, "remote1": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def ep_rule_action2(memories_info: List["MemoryInfo"], args: Arguments) -> Tuple[BBPSSW, List[None], List[None], List[None]]:
    """Action function used by BBPSSW protocol on nodes except the responder
    """
    memories = [info.memory for info in memories_info]
    name = "EP.%s" % memories[0].name
    protocol = BBPSSW(None, name, memories[0], None)
    return protocol, [None], [None], [None]


def ep_req_func1(protocols, args: Arguments) -> BBPSSW:
    """Function used by `ep_rule_action1` for selecting purification protocols on the remote node
       Will 'combine two BBPSSW into one BBPSSW'

    Args:
        protocols (list): a list of waiting protocols
        args (dict): the arguments
    Return:
        the selected protocol
    """
    remote0 = args["remote0"]
    remote1 = args["remote1"]

    _protocols = []
    for protocol in protocols:
        if not isinstance(protocol, BBPSSW):
            continue

        if protocol.kept_memo.name == remote0:
            _protocols.insert(0, protocol)
        if protocol.kept_memo.name == remote1:
            _protocols.insert(1, protocol)

    if len(_protocols) != 2:
        return None

    protocols.remove(_protocols[1])
    _protocols[1].rule.protocols.remove(_protocols[1])
    _protocols[1].kept_memo.detach(_protocols[1])
    _protocols[0].meas_memo = _protocols[1].kept_memo
    _protocols[0].memories = [_protocols[0].kept_memo, _protocols[0].meas_memo]
    _protocols[0].name = _protocols[0].name + "." + _protocols[0].meas_memo.name
    _protocols[0].meas_memo.attach(_protocols[0])

    return _protocols[0]


def ep_rule_condition1(memory_info: "MemoryInfo", memory_manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by BBPSSW protocol on nodes except the initiator
    """
    memory_indices = args["memory_indices"]
    reservation = args["reservation"]
    if (memory_info.index in memory_indices                              # this memory (kept)
            and memory_info.state == "ENTANGLED"
            and memory_info.fidelity < reservation.fidelity):
        for info in memory_manager:
            if (info != memory_info and info.index in memory_indices     # another memory (meas)
                    and info.state == "ENTANGLED"
                    and info.remote_node == memory_info.remote_node
                    and info.fidelity == memory_info.fidelity):
                assert memory_info.remote_memo != info.remote_memo
                return [memory_info, info]
    return []


def ep_rule_condition2(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by BBPSSW protocol on nodes except the responder
    """
    memory_indices = args["memory_indices"]
    fidelity = args["fidelity"]

    if (memory_info.index in memory_indices and memory_info.state == "ENTANGLED" and memory_info.fidelity < fidelity):
        return [memory_info]
    return []


# entanglement swapping

def es_rule_actionA(memories_info: List["MemoryInfo"], args: Arguments) -> Tuple[EntanglementSwappingA, List[str], List["es_req_func"], List[Dict]]:
    """Action function used by EntanglementSwappingA protocol on nodes
    """
    es_succ_prob = args["es_succ_prob"]
    es_degradation = args["es_degradation"]
    memories = [info.memory for info in memories_info]
    protocol = EntanglementSwappingA(None, "ESA.{}.{}".format(memories[0].name, memories[1].name),
                                     memories[0], memories[1], success_prob=es_succ_prob, degradation=es_degradation)
    dsts = [info.remote_node for info in memories_info]
    req_funcs = [es_req_func, es_req_func]
    req_args = [{"target_memo": memories_info[0].remote_memo}, {"target_memo": memories_info[1].remote_memo}]
    return protocol, dsts, req_funcs, req_args


def es_rule_actionB(memories_info: List["MemoryInfo"], args: Arguments) -> Tuple[EntanglementSwappingB, List[None], List[None], List[None]]:
    """Action function used by EntanglementSwappingB protocol
    """
    memories = [info.memory for info in memories_info]
    memory = memories[0]
    protocol = EntanglementSwappingB(None, "ESB." + memory.name, memory)
    return protocol, [None], [None], [None]


def es_req_func(protocols: List["EntanglementProtocol"], args: Arguments) -> EntanglementSwappingB:
    """Function used by `es_rule_actionA` for selecting swapping protocols on the remote node

    Args:
        protocols (list): a list of waiting protocols
        args (dict): the arguments
    Return:
        the selected protocol
    """
    target_memo = args["target_memo"]
    for protocol in protocols:
        if (isinstance(protocol, EntanglementSwappingB)
                # and protocol.memory.name == memories_info[0].remote_memo):
                and protocol.memory.name == target_memo):
            return protocol


def es_rule_conditionA(memory_info: "MemoryInfo", memory_manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by EntanglementSwappingA protocol on nodes
    """
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if (memory_info.state == "ENTANGLED"
            and memory_info.index in memory_indices
            and memory_info.remote_node == left
            and memory_info.fidelity >= fidelity):
        for memory_info2 in memory_manager:
            if (memory_info2.state == "ENTANGLED"
                    and memory_info2.index in memory_indices
                    and memory_info2.remote_node == right
                    and memory_info2.fidelity >= fidelity):
                return [memory_info, memory_info2]
    elif (memory_info.state == "ENTANGLED"
            and memory_info.index in memory_indices
            and memory_info.remote_node == right
            and memory_info.fidelity >= fidelity):
        for memory_info2 in memory_manager:
            if (memory_info2.state == "ENTANGLED"
                    and memory_info2.index in memory_indices
                    and memory_info2.remote_node == left
                    and memory_info2.fidelity >= fidelity):
                return [memory_info, memory_info2]
    return []


def es_rule_conditionB1(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by EntanglementSwappingB protocol on nodes of either responder or initiator
    """
    memory_indices = args["memory_indices"]
    target_remote = args["target_remote"]  # A - B - C. For A: B is the remote node, C is the target remote
    fidelity = args["fidelity"]
    if (memory_info.state == "ENTANGLED"
            and memory_info.index in memory_indices
            # and memory_info.remote_node != path[-1]
            and memory_info.remote_node != target_remote
            # and memory_info.fidelity >= reservation.fidelity):
            and memory_info.fidelity >= fidelity):
        return [memory_info]
    else:
        return []


def es_rule_conditionB2(memory_info: "MemoryInfo", manager: "MemoryManager", args: Arguments) -> List["MemoryInfo"]:
    """Condition function used by EntanglementSwappingB protocol on intermediate nodes of path
    """
    memory_indices = args["memory_indices"]
    left = args["left"]
    right = args["right"]
    fidelity = args["fidelity"]
    if (memory_info.state == ENTANGLED
            and memory_info.index in memory_indices
            and memory_info.remote_node not in [left, right]
            and memory_info.fidelity >= fidelity):
        return [memory_info]
    else:
        return []


class ResourceReservationProtocol(StackProtocol):
    """ReservationProtocol for node resources.

    The reservation protocol receives network entanglement requests and attempts to reserve local resources.
    If successful, it will forward the request to another node in the entanglement path and create local rules.
    These rules are passed to the node's resource manager.
    If unsuccessful, the protocol will notify the network manager of failure.

    Attributes:
        owner (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        memo_arr (MemoryArray): memory array to track.
        timecards (List[MemoryTimeCard]): list of reservation cards for all memories on node.
        es_succ_prob (float): sets `success_probability` of `EntanglementSwappingA` protocols created by rules.
        es_degradation (float): sets `degradation` of `EntanglementSwappingA` protocols created by rules.
        accepted_reservations (List[Reservation]): list of all approved reservation requests.
    """

    def __init__(self, owner: "QuantumRouter", name: str, memory_array_name: str):
        """Constructor for the reservation protocol class.

        Args:
            owner (QuantumRouter): node to attach protocol to.
            name (str): label for reservation protocol instance.
            memory_array_name (str): name of the memory array component on own.
        """

        super().__init__(owner, name)
        self.memo_arr = owner.components[memory_array_name]
        self.timecards = [MemoryTimeCard(i) for i in range(len(self.memo_arr))]
        self.es_succ_prob = 1
        self.es_degradation = 0.95
        self.accepted_reservations = []

    def push(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float,
             entanglement_number: int = 1, identity: int = 0):
        """Method to receive reservation requests from higher level protocol.

        Will evaluate request and determine if node can meet it.
        If it can, it will push the request down to a lower protocol.
        Otherwise, it will pop the request back up.

        Args:
            responder (str): node that entanglement is requested with.
            start_time (int): simulation time at which entanglement should start.
            end_time (int): simulation time at which entanglement should cease.
            memory_size (int): number of memories to be entangled.
            target_fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement the request ask for.
            identity (int): the ID of the request.
        Side Effects:
            May push/pop to lower/upper attached protocols (or network manager).
        """

        reservation = Reservation(self.owner.name, responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity)
        if self.schedule(reservation):
            msg = ResourceReservationMessage(RSVPMsgType.REQUEST, self.name, reservation)
            qcap = QCap(self.owner.name)
            msg.qcaps.append(qcap)
            self._push(dst=responder, msg=msg)
        else:
            msg = ResourceReservationMessage(RSVPMsgType.REJECT, self.name, reservation, path=[])
            self._pop(msg=msg)

    def pop(self, src: str, msg: "ResourceReservationMessage"):
        """Method to receive messages from lower protocols.
        Messages may be of 3 types, causing different network manager behavior:

        1. REQUEST: requests are evaluated, and forwarded along the path if accepted.
            Otherwise, a REJECT message is sent back.
        2. REJECT: any reserved resources are released and the message forwarded back towards the initializer.
        3. APPROVE: rules are created to achieve the approved request.
            The message is forwarded back towards the initializer.

        Args:
            src (str): source node of the message.
            msg (ResourceReservationMessage): message received.
        
        Side Effects:
            May push/pop to lower/upper attached protocols (or network manager).

        Assumption:
            the path initiator -> responder is same as the reverse path
        """

        if msg.msg_type == RSVPMsgType.REQUEST:
            assert self.owner.timeline.now() < msg.reservation.start_time
            qcap = QCap(self.owner.name)
            msg.qcaps.append(qcap)
            path = [qcap.node for qcap in msg.qcaps]
            if self.schedule(msg.reservation):  # schedule success
                if self.owner.name == msg.reservation.responder:
                    rules = self.create_rules(path, reservation=msg.reservation)
                    self.load_rules(rules, msg.reservation)
                    msg.reservation.set_path(path)
                    new_msg = ResourceReservationMessage(RSVPMsgType.APPROVE, self.name, msg.reservation, path=path)
                    self._pop(msg=msg)
                    self._push(dst=None, msg=new_msg, next_hop=src)
                else:
                    self._push(dst=msg.reservation.responder, msg=msg)
            else:                               # schedule failed
                new_msg = ResourceReservationMessage(RSVPMsgType.REJECT, self.name, msg.reservation, path=path)
                self._push(dst=None, msg=new_msg, next_hop=src)
        elif msg.msg_type == RSVPMsgType.REJECT:
            for card in self.timecards:
                card.remove(msg.reservation)
            if msg.reservation.initiator == self.owner.name:
                self._pop(msg=msg)
            else:
                next_hop = self.next_hop_when_tracing_back(msg.path)
                self._push(dst=None, msg=msg, next_hop=next_hop)
        elif msg.msg_type == RSVPMsgType.APPROVE:
            rules = self.create_rules(msg.path, msg.reservation)
            self.load_rules(rules, msg.reservation)
            if msg.reservation.initiator == self.owner.name:
                self._pop(msg=msg)
            else:
                next_hop = self.next_hop_when_tracing_back(msg.path)
                self._push(dst=None, msg=msg, next_hop=next_hop)
        else:
            raise Exception("Unknown type of message", msg.msg_type)

    def next_hop_when_tracing_back(self, path: List[str]) -> str:
        '''the next hop when going back from the responder to the initiator

        Args:
            path (List[str]): a list of router names that goes from initiator to responder
        Return:
            str: the name of the next hop
        '''
        cur_index = path.index(self.owner.name)
        assert cur_index >= 1, f'{cur_index} must be larger equal than 1'
        next_hop = path[cur_index - 1]
        return next_hop

    def schedule(self, reservation: "Reservation") -> bool:
        """Method to attempt reservation request. If attempt succeeded, return True; otherwise, return False.

        Args:
            reservation (Reservation): reservation to approve or reject.

        Returns:
            bool: if reservation can be met or not.
        """

        if self.owner.name in [reservation.initiator, reservation.responder]:
            counter = reservation.memory_size
        else:  # e.g., entanglement swapping nodes needs twice amount of memory
            counter = reservation.memory_size * 2
        timecards = []
        for timecard in self.timecards:
            if timecard.add(reservation):
                counter -= 1
                timecards.append(timecard)
            if counter == 0:  # attempt reservation succeeded: enough memory (timecard)
                break

        if counter > 0:       # attempt reservation failed: not enough memory (timecard)
            for timecard in timecards:
                timecard.remove(reservation)  # remove reservation from the timecard that have added the reservation
            return False

        return True

    def create_rules(self, path: List[str], reservation: "Reservation") -> List["Rule"]:
        """Method to create rules for a successful request.

        Rules are used to direct the flow of information/entanglement in the resource manager.

        Args:
            path (List[str]): list of node names in entanglement path.
            reservation (Reservation): approved reservation.

        Returns:
            List[Rule]: list of rules created by the method.
        """

        rules = []
        memory_indices = []
        for card in self.timecards:
            if reservation in card.reservations:
                memory_indices.append(card.memory_index)

        index = path.index(self.owner.name)  # the location of this node along the path from initiator to responder

        # 1. create rules for entanglement generation
        if index > 0:
            condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
            action_args = {"mid": self.owner.map_to_middle_node[path[index - 1]],
                           "path": path, "index": index}
            rule = Rule(10, eg_rule_action1, eg_rule_condition, action_args, condition_args)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
            else:
                condition_args = {"memory_indices": memory_indices[reservation.memory_size:]}

            action_args = {"mid": self.owner.map_to_middle_node[path[index + 1]],
                           "path": path, "index": index, "name": self.owner.name, "reservation": reservation}
            rule = Rule(10, eg_rule_action2, eg_rule_condition, action_args, condition_args)
            rules.append(rule)

        # 2. create rules for entanglement purification
        if index > 0:
            condition_args = {"memory_indices": memory_indices[:reservation.memory_size], "reservation": reservation}
            action_args = {}
            rule = Rule(10, ep_rule_action1, ep_rule_condition1, action_args, condition_args)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                condition_args = {"memory_indices": memory_indices, "fidelity": reservation.fidelity}
            else:
                condition_args = {"memory_indices": memory_indices[reservation.memory_size:], "fidelity": reservation.fidelity}

            action_args = {}
            rule = Rule(10, ep_rule_action2, ep_rule_condition2, action_args, condition_args)
            rules.append(rule)

        # 3. create rules for entanglement swapping
        if index == 0:
            condition_args = {"memory_indices": memory_indices, "target_remote": path[-1], "fidelity": reservation.fidelity}
            action_args = {}
            rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
            rules.append(rule)
        elif index == len(path) - 1:
            action_args = {}
            condition_args = {"memory_indices": memory_indices, "target_remote": path[0], "fidelity": reservation.fidelity}
            rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
            rules.append(rule)
        else:
            _path = path[:]
            while _path.index(self.owner.name) % 2 == 0:
                new_path = []
                for i, n in enumerate(_path):
                    if i % 2 == 0 or i == len(_path) - 1:
                        new_path.append(n)
                _path = new_path
            _index = _path.index(self.owner.name)
            left, right = _path[_index - 1], _path[_index + 1]

            condition_args = {"memory_indices": memory_indices, "left": left, "right": right, "fidelity": reservation.fidelity}
            action_args = {"es_succ_prob": self.es_succ_prob, "es_degradation": self.es_degradation}
            rule = Rule(10, es_rule_actionA, es_rule_conditionA, action_args, condition_args)
            rules.append(rule)

            action_args = {}
            rule = Rule(10, es_rule_actionB, es_rule_conditionB2, action_args, condition_args)
            rules.append(rule)

        for rule in rules:
            rule.set_reservation(reservation)

        return rules

    def load_rules(self, rules: List["Rule"], reservation: "Reservation") -> None:
        """Method to add created rules to resource manager.

        This method will schedule the resource manager to load all rules at the reservation start time.
        The rules will be set to expire at the reservation end time.

        Args:
            rules (List[Rules]): rules to add.
            reservation (Reservation): reservation that created the rules.
        """

        self.accepted_reservations.append(reservation)

        for rule in rules:
            process = Process(self.owner.resource_manager, "load", [rule])
            event = Event(reservation.start_time, process, self.owner.timeline.schedule_counter)
            self.owner.timeline.schedule(event)
            
            process = Process(self.owner.resource_manager, "expire", [rule])
            event = Event(reservation.end_time, process, self.owner.timeline.schedule_counter)
            self.owner.timeline.schedule(event)

        for card in self.timecards:
            if reservation in card.reservations:
                process = Process(self.owner.resource_manager, "update", [None, self.memo_arr[card.memory_index], "RAW"])
                event = Event(reservation.end_time, process, self.owner.timeline.schedule_counter)
                self.owner.timeline.schedule(event)

    def received_message(self, src, msg):
        """Method to receive messages directly (should not be used; receive through network manager)."""

        raise Exception("RSVP protocol {} received a message (disallowed)".format(self.name))

    def set_swapping_success_rate(self, prob: float) -> None:
        assert 0 <= prob <= 1
        self.es_succ_prob = prob

    def set_swapping_degradation(self, degradation: float) -> None:
        assert 0 <= degradation <= 1
        self.es_degradation = degradation


class Reservation:
    """Tracking of reservation parameters for the network manager.
       Each request will generate a reservation

    Attributes:
        initiator (str): name of the node that created the reservation request.
        responder (str): name of distant node with witch entanglement is requested.
        start_time (int): simulation time at which entanglement should be attempted.
        end_time (int): simulation time at which resources may be released.
        memory_size (int): number of entangled memory pairs requested.
        path (list): a list of router names from the source to destination
        entanglement_number (int): the number of entanglement pair that the request ask for.
        identity (int): the ID of a request.
    """

    def __init__(self, initiator: str, responder: str, start_time: int,
                 end_time: int, memory_size: int, fidelity: float, entanglement_number: int = 1, identity: int = 0):
        """Constructor for the reservation class.

        Args:
            initiator (str): node initiating the request.
            responder (str): node with which entanglement is requested.
            start_time (int): simulation start time of entanglement.
            end_time (int): simulation end time of entanglement.
            memory_size (int): number of entangled memories requested.
            fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement the request ask for.
            identity (int): the ID of a request
        """

        self.initiator = initiator
        self.responder = responder
        self.start_time = start_time
        self.end_time = end_time
        self.memory_size = memory_size
        self.fidelity = fidelity
        self.entanglement_number = entanglement_number
        self.identity = identity
        self.path = []
        assert self.start_time < self.end_time
        assert self.memory_size > 0

    def __str__(self) -> str:
        s = "|initiator={}; responder={}; start_time={:,}; end_time={:,}; memory_size={}; target_fidelity={}; entanglement_number={}; identity={}|".format(
              self.initiator, self.responder, int(self.start_time), int(self.end_time), self.memory_size, self.fidelity, self.entanglement_number, self.identity)
        return s

    def __repr__(self) -> str:
        return self.__str__()

    def set_path(self, path: List[str]):
        self.path = path

    def __eq__(self, other: "Reservation") -> bool:
        return other.initiator == self.initiator and \
               other.responder == self.responder and \
               other.start_time == self.start_time and \
               other.end_time == self.end_time and \
               other.memory_size == self.memory_size and \
               other.fidelity == self.fidelity

    def __lt__(self, other: "Reservation") -> bool:
        return self.identity < other.identity

    def __hash__(self):
        return hash((self.initiator, self.responder, self.start_time, self.end_time, self.memory_size, self.fidelity))


class MemoryTimeCard:
    """Class for tracking reservations on a specific memory.
       Each quantum memory in a memory array is associated with a memory time card

    Attributes:
        memory_index (int): index of memory being tracked (in memory array).
        reservations (List[Reservation]): list of reservations for the memory.
    """

    def __init__(self, memory_index: int):
        """Constructor for time card class.

        Args:
            memory_index (int): index of memory to track.
        """

        self.memory_index = memory_index
        self.reservations = []

    def add(self, reservation: "Reservation") -> bool:
        """Method to add reservation.

        Will use `schedule_reservation` method to determine index to insert reservation.

        Args:
            reservation (Reservation): reservation to add.

        Returns:
            bool: whether reservation was inserted successfully.
        """
        
        position = self.schedule_reservation(reservation)
        if position >= 0:
            self.reservations.insert(position, reservation)
            return True
        else:
            return False

    def remove(self, reservation: "Reservation") -> bool:
        """Method to remove a reservation.

        Args:
            reservation (Reservation): reservation to remove.

        Returns:
            bool: if reservation was already on the memory (return True) or not (return False).
        """

        try:
            position = self.reservations.index(reservation)
            self.reservations.pop(position)
            return True
        except ValueError:
            return False

    def schedule_reservation(self, reservation: "Reservation") -> int:
        """Method to add reservation to a memory.

        Will return index at which reservation can be inserted into memory reservation list.
        If no space found for reservation, will raise an exception.

        Args:
            reservation (Reservation): reservation to schedule.

        Returns:
            int: index to insert reservation in reservation list.

        Raises:
            Exception: no valid index to insert reservation.
        """

        start, end = 0, len(self.reservations) - 1
        while start <= end:
            mid = (start + end) // 2
            if self.reservations[mid].start_time > reservation.end_time:
                end = mid - 1
            elif self.reservations[mid].end_time < reservation.start_time:
                start = mid + 1
            elif (max(self.reservations[mid].start_time, reservation.start_time) <=
                    min(self.reservations[mid].end_time, reservation.end_time)):
                return -1
            else:
                raise Exception("Unexpected status")
        return start


class QCap:
    """Quantum Capacity. Class to collect local information for the reservation protocol

    Attributes:
        node (str): name of current node.
    """

    def __init__(self, node: str):
        self.node = node
