"""Definition of Reservation protocol and related tools.

This module provides a definition for the reservation protocol used by the network manager.
This includes the Reservation, MemoryTimeCard, and QCap classes, which are used by the network manager to track reservations.
Also included is the definition of the message type used by the reservation protocol.
"""

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter

from ..message import Message
from ..protocol import StackProtocol

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
        qcaps (list[QCaps]): cumulative quantum capacity object list (if `msg_type == REQUEST`)
        path (list[str]): cumulative node list for entanglement path (if `msg_type == APPROVE` or `msg_type == REJECT`)
    """

    def __init__(self, msg_type, receiver: str, reservation: "Reservation", **kwargs):
        super().__init__(msg_type, receiver)
        self.reservation = reservation
        match self.msg_type:
            case RSVPMsgType.REQUEST:
                self.qcaps = []
            case RSVPMsgType.REJECT:
                self.path = kwargs['path']
            case RSVPMsgType.APPROVE:
                self.path = kwargs['path']
            case _:
                raise Exception("Unknown message type")


    def __str__(self):
        return f"|type={self.msg_type}; reservation={self.reservation}|"

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
        timecards (list[MemoryTimeCard]): list of reservation cards for all memories on node.
        es_succ_prob (float): sets `success_probability` of `EntanglementSwappingA` protocols created by rules.
        es_degradation (float): sets `degradation` of `EntanglementSwappingA` protocols created by rules.
        accepted_reservations (list[Reservation]): list of all approved reservation requests.
    """

    def __init__(self, owner: "QuantumRouter", name: str, memory_array_name: str):
        """Constructor for the reservation protocol class.

        Args:
            owner (QuantumRouter): node to attach protocol to.
            name (str): label for reservation protocol instance.
            memory_array_name (str): name of the memory array component on own.
        """

        super().__init__(owner, name)
        self.memory_array_name = memory_array_name
        self.memo_arr = owner.components[memory_array_name]
        self.timecards = [MemoryTimeCard(i) for i in range(len(self.memo_arr))]
        self.purification_mode = 'until_target'  # once or until_target. QoS
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

        reservation = Reservation(self.owner.name, responder, start_time, end_time, memory_size, target_fidelity,
                                  entanglement_number, identity)
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
                    self.owner.resource_manager.generate_load_rules(path, msg.reservation, self.timecards, self.memory_array_name)
                    self.accepted_reservations.append(msg.reservation)
                    msg.reservation.set_path(path)
                    new_msg = ResourceReservationMessage(RSVPMsgType.APPROVE, self.name, msg.reservation, path=path)
                    self._pop(msg=msg)
                    self._push(dst=None, msg=new_msg, next_hop=src)
                else:
                    self._push(dst=msg.reservation.responder, msg=msg)
            else:  # schedule failed
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
            self.owner.resource_manager.generate_load_rules(msg.path, msg.reservation, self.timecards, self.memory_array_name)
            self.accepted_reservations.append(msg.reservation)
            if msg.reservation.initiator == self.owner.name:
                self._pop(msg=msg)
            else:
                next_hop = self.next_hop_when_tracing_back(msg.path)
                self._push(dst=None, msg=msg, next_hop=next_hop)
        else:
            raise Exception("Unknown type of message", msg.msg_type)

    def next_hop_when_tracing_back(self, path: list[str]) -> str:
        '''the next hop when going back from the responder to the initiator

        Args:
            path (list[str]): a list of router names that goes from initiator to responder
        Returns:
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

        if counter > 0:  # attempt reservation failed: not enough memory (timecard)
            for timecard in timecards:
                timecard.remove(reservation)  # remove reservation from the timecard that have added the reservation
            return False

        return True

    def received_message(self, src, msg):
        """Method to receive messages directly (should not be used; receive through network manager)."""

        raise Exception(f"RSVP protocol {self.name} received a message (disallowed)")

    # def set_swapping_success_rate(self, prob: float) -> None:
    #     assert 0 <= prob <= 1
    #     self.es_succ_prob = prob

    # def set_swapping_degradation(self, degradation: float) -> None:
    #     assert 0 <= degradation <= 1
    #     self.es_degradation = degradation

    def set_purification_mode(self, mode: str) -> None:
        assert mode in ['once', 'until_target'], \
            f'Purification mode {mode} not supported, should be either "once" or "until_target"'
        self.purification_mode = mode


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
            path
            purification_mode
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
        self.purification_mode: str = 'until_target'
        assert self.start_time < self.end_time
        assert self.memory_size > 0

    def __str__(self) -> str:
        return f'|initiator={self.initiator}; responder={self.responder}; start_time={self.start_time:,}; end_time={self.end_time:,}; memory_size={self.memory_size}; target_fidelity={self.fidelity}; entanglement_number={self.entanglement_number}; identity={self.identity}|'

    def __repr__(self) -> str:
        return self.__str__()

    def set_path(self, path: list[str]):
        self.path = path

    def __eq__(self, other: "Reservation"):
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
        reservations (list[Reservation]): list of reservations for the memory.
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
        return start


class QCap:
    """Quantum Capacity. Class to collect local information for the reservation protocol

    Attributes:
        node (str): name of current node.
    """

    def __init__(self, node: str):
        self.node = node
