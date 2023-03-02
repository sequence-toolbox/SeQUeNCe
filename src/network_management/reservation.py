"""Definition of Reservation protocol and related tools.

This module provides a definition for the reservation protocol used by the network manager.
This includes the Reservation, MemoryTimeCard, and QCap classes, which are used by the network manager to track reservations.
Also included is the definition of the message type used by the reservation protocol.
"""

from enum import Enum, auto
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter

from .rule_args import *
from ..resource_management.rule_manager import Rule
from ..message import Message
from ..protocol import StackProtocol
from ..kernel.event import Event
from ..kernel.process import Process


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
        msg_type (GenerationMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        reservation (Reservation): reservation object relayed between nodes.
        qcaps (List[QCaps]): cumulative quantum capacity object list (if `msg_type == REQUEST`)
        path (List[str]): cumulative node list for entanglement path (if `msg_type == APPROVE`)
    """

    def __init__(self, msg_type: any, receiver: str, reservation: "Reservation", **kwargs):
        Message.__init__(self, msg_type, receiver)
        self.reservation = reservation
        if self.msg_type is RSVPMsgType.REQUEST:
            self.qcaps = []
        elif self.msg_type is RSVPMsgType.REJECT:
            pass
        elif self.msg_type is RSVPMsgType.APPROVE:
            self.path = kwargs["path"]
        else:
            raise Exception("Unknown type of message")

    def __str__(self):
        return f"ResourceReservationProtocol: \n\ttype={self.msg_type}, " \
               f"\n\treservation={self.reservation}"


class ResourceReservationProtocol(StackProtocol):
    """ReservationProtocol for  node resources.

    The reservation protocol receives network entanglement requests and attempts to reserve local resources.
    If successful, it will forward the request to another node in the entanglement path and create local rules.
    These rules are passed to the node's resource manager.
    If unsuccessful, the protocol will notify the network manager of failure.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        memo_arr (MemoryArray): memory array to track.
        timecards (List[MemoryTimeCard]): list of reservation cards for all memories on node.
        es_succ_prob (float): sets `success_probability` of `EntanglementSwappingA` protocols created by rules.
        es_degradation (float): sets `degradation` of `EntanglementSwappingA` protocols created by rules.
        accepted_reservation (List[Reservation]): list of all approved reservation requests.
    """

    def __init__(self, own: "QuantumRouter", name: str, memory_array_name: str):
        """Constructor for the reservation protocol class.

        Args:
            own (QuantumRouter): node to attach protocol to.
            name (str): label for reservation protocol instance.
            memory_array_name (str): name of the memory array component on own.
        """

        super().__init__(own, name)
        self.memo_arr = own.components[memory_array_name]
        self.timecards = [MemoryTimeCard(i) for i in range(len(self.memo_arr))]
        self.es_succ_prob = 1
        self.es_degradation = 0.95
        self.accepted_reservation = []

    def push(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float):
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

        Side Effects:
            May push/pop to lower/upper attached protocols (or network manager).
        """

        reservation = Reservation(self.own.name, responder, start_time, end_time, memory_size, target_fidelity)
        if self.schedule(reservation):
            msg = ResourceReservationMessage(RSVPMsgType.REQUEST, self.name, reservation)
            qcap = QCap(self.own.name)
            msg.qcaps.append(qcap)
            self._push(dst=responder, msg=msg)
        else:
            msg = ResourceReservationMessage(RSVPMsgType.REJECT, self.name,
                                             reservation, path=[])
            self._pop(msg=msg)

    def pop(self, src: str, msg: "ResourceReservationMessage"):
        """Method to receive messages from lower protocols.

        Messages may be of 3 types, causing different network manager behavior:

        1. REQUEST: requests are evaluated, and forwarded along the path if accepted. Otherwise a REJECT message is sent back.
        2. REJECT: any reserved resources are released and the message forwarded back towards the initializer.
        3. APPROVE: rules are created to achieve the approved request. The message is forwarded back towards the initializer.

        Args:
            src (str): source node of the message.
            msg (ResourceReservationMessage): message received.
        
        Side Effects:
            May push/pop to lower/upper attached protocols (or network manager).

        Assumption:
            the path initiator -> responder is same as the reverse path
        """

        if msg.msg_type == RSVPMsgType.REQUEST:
            assert self.own.timeline.now() < msg.reservation.start_time
            if self.schedule(msg.reservation):
                qcap = QCap(self.own.name)
                msg.qcaps.append(qcap)
                if self.own.name == msg.reservation.responder:
                    path = [qcap.node for qcap in msg.qcaps]
                    rules = self.create_rules(path, reservation=msg.reservation)
                    self.load_rules(rules, msg.reservation)
                    msg.reservation.set_path(path)
                    new_msg = ResourceReservationMessage(RSVPMsgType.APPROVE,
                                                         self.name,
                                                         msg.reservation,
                                                         path=path)
                    self._pop(msg=msg)
                    self._push(dst=msg.reservation.initiator, msg=new_msg)
                else:
                    self._push(dst=msg.reservation.responder, msg=msg)
            else:
                new_msg = ResourceReservationMessage(RSVPMsgType.REJECT,
                                                     self.name,
                                                     msg.reservation)
                self._push(dst=msg.reservation.initiator, msg=new_msg)
        elif msg.msg_type == RSVPMsgType.REJECT:
            for card in self.timecards:
                card.remove(msg.reservation)
            if msg.reservation.initiator == self.own.name:
                self._pop(msg=msg)
            else:
                self._push(dst=msg.reservation.initiator, msg=msg)
        elif msg.msg_type == RSVPMsgType.APPROVE:
            rules = self.create_rules(msg.path, msg.reservation)
            self.load_rules(rules, msg.reservation)
            if msg.reservation.initiator == self.own.name:
                self._pop(msg=msg)
            else:
                self._push(dst=msg.reservation.initiator, msg=msg)
        else:
            raise Exception("Unknown type of message", msg.msg_type)

    def schedule(self, reservation: "Reservation") -> bool:
        """Method to attempt reservation request.

        Args:
            reservation (Reservation): reservation to approve or reject.

        Returns:
            bool: if reservation can be met or not.
        """

        if self.own.name in [reservation.initiator, reservation.responder]:
            counter = reservation.memory_size
        else:
            counter = reservation.memory_size * 2
        cards = []
        for card in self.timecards:
            if card.add(reservation):
                counter -= 1
                cards.append(card)
            if counter == 0:
                break

        if counter > 0:
            for card in cards:
                card.remove(reservation)
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

        # create rules for entanglement generation
        index = path.index(self.own.name)
        if index > 0:
            condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
            action_args = {"mid": self.own.map_to_middle_node[path[index - 1]],
                           "path": path, "index": index}
            rule = Rule(10, eg_rule_action1, eg_rule_condition, action_args, condition_args)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                condition_args = {"memory_indices": memory_indices[:reservation.memory_size]}
            else:
                condition_args = {"memory_indices":
                                      memory_indices[reservation.memory_size:]}

            action_args = {"mid": self.own.map_to_middle_node[path[index + 1]],
                           "path": path, "index": index, "name": self.own.name,
                           "reservation": reservation}
            rule = Rule(10, eg_rule_action2, eg_rule_condition, action_args, condition_args)
            rules.append(rule)

        # create rules for entanglement purification
        if index > 0:
            condition_args = {"memory_indices":
                                  memory_indices[:reservation.memory_size],
                              "reservation": reservation}
            action_args = {}
            rule = Rule(10, ep_rule_action1, ep_rule_condition1, action_args, condition_args)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                condition_args = {"memory_indices": memory_indices,
                                  "fidelity": reservation.fidelity}
            else:
                condition_args = {"memory_indices": memory_indices[reservation.memory_size:],
                                  "fidelity": reservation.fidelity}

            action_args = {}
            rule = Rule(10, ep_rule_action2, ep_rule_condition2, action_args, condition_args)
            rules.append(rule)

        # create rules for entanglement swapping
        if index == 0:
            condition_args = {"memory_indices": memory_indices,
                              "target_remote": path[-1],
                              "fidelity": reservation.fidelity}
            action_args = {}
            rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
            rules.append(rule)

        elif index == len(path) - 1:
            action_args = {}
            condition_args = {"memory_indices": memory_indices,
                              "target_remote": path[0],
                              "fidelity": reservation.fidelity}
            rule = Rule(10, es_rule_actionB, es_rule_conditionB1, action_args, condition_args)
            rules.append(rule)

        else:
            _path = path[:]
            while _path.index(self.own.name) % 2 == 0:
                new_path = []
                for i, n in enumerate(_path):
                    if i % 2 == 0 or i == len(_path) - 1:
                        new_path.append(n)
                _path = new_path
            _index = _path.index(self.own.name)
            left, right = _path[_index - 1], _path[_index + 1]

            condition_args = {"memory_indices": memory_indices,
                              "left": left,
                              "right": right,
                              "fidelity": reservation.fidelity}
            action_args = {"es_succ_prob": self.es_succ_prob,
                           "es_degradation": self.es_degradation}
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

        self.accepted_reservation.append(reservation)

        # reset all memories after a reservation is finished (DON'T NEED FOR ADAPTIVE)
        # for card in self.timecards:
        #     if reservation in card.reservations:
        #         process = Process(self.own.resource_manager, "update",
        #                           [None, self.memo_arr[card.memory_index], "RAW"])
        #         event = Event(reservation.end_time, process, 1)
        #         self.own.timeline.schedule(event)

        for rule in rules:
            process = Process(self.own.resource_manager, "load", [rule])
            event = Event(reservation.start_time, process)
            self.own.timeline.schedule(event)
            process = Process(self.own.resource_manager, "expire", [rule])
            event = Event(reservation.end_time, process, 0)
            self.own.timeline.schedule(event)

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

    Attributes:
        initiator (str): name of the node that created the reservation request.
        responder (str): name of distant node with witch entanglement is requested.
        start_time (int): simulation time at which entanglement should be attempted.
        end_time (int): simulation time at which resources may be released.
        memory_size (int): number of entangled memory pairs requested.
    """

    def __init__(self, initiator: str, responder: str, start_time: int,
                 end_time: int, memory_size: int, fidelity: float):
        """Constructor for the reservation class.

        Args:
            initiator (str): node initiating the request.
            responder (str): node with which entanglement is requested.
            start_time (int): simulation start time of entanglement.
            end_time (int): simulation end time of entanglement.
            memory_size (int): number of entangled memories requested.
            fidelity (float): desired fidelity of entanglement.
        """

        self.initiator = initiator
        self.responder = responder
        self.start_time = start_time
        self.end_time = end_time
        self.memory_size = memory_size
        self.fidelity = fidelity
        self.path = []
        assert self.start_time < self.end_time
        assert self.memory_size > 0

    def set_path(self, path: List[str]):
        self.path = path

    def __str__(self):
        return f"Reservation: initiator={self.initiator}, " \
               f"responder={self.responder}, start_time={self.start_time}, " \
               f"end_time={self.end_time}, memory_size={self.memory_size}, " \
               f"target_fidelity={self.fidelity}"

    def __eq__(self, other: "Reservation"):
        return other.initiator == self.initiator and \
               other.responder == self.responder and \
               other.start_time == self.start_time and \
               other.end_time == self.end_time and \
               other.memory_size == self.memory_size and \
               other.fidelity == self.fidelity


class MemoryTimeCard:
    """Class for tracking reservations on a specific memory.

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
            bool: whether or not reservation was inserted successfully.
        """
        
        pos = self.schedule_reservation(reservation)
        if pos >= 0:
            self.reservations.insert(pos, reservation)
            return True
        else:
            return False

    def remove(self, reservation: "Reservation") -> bool:
        """Method to remove a reservation.

        Args:
            reservation (Reservation): reservation to remove.

        Returns:
            bool: if reservation was already on the memory or not.
        """

        try:
            pos = self.reservations.index(reservation)
            self.reservations.pop(pos)
            return True
        except ValueError:
            return False

    def schedule_reservation(self, resv: "Reservation") -> int:
        """Method to add reservation to a memory.

        Will return index at which reservation can be inserted into memory reservation list.
        If no space found for reservation, will raise an exception.

        Args:
            resv (Reservation): reservation to schedule.

        Returns:
            int: index to insert reservation in reservation list.

        Raises:
            Exception: no valid index to insert reservation.
        """

        start, end = 0, len(self.reservations) - 1
        while start <= end:
            mid = (start + end) // 2
            if self.reservations[mid].start_time > resv.end_time:
                end = mid - 1
            elif self.reservations[mid].end_time < resv.start_time:
                start = mid + 1
            elif (max(self.reservations[mid].start_time, resv.start_time)
                  <= min(self.reservations[mid].end_time, resv.end_time)):
                return -1
            else:
                raise Exception("Unexpected status")
        return start


class QCap():
    """Class to collect local information for the reservation protocol

    Attributes:
        node (str): name of current node.
    """

    def __init__(self, node: str):
        self.node = node
