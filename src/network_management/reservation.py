"""Definition of Reservation protocol and related tools.

This module provides a definition for the reservation protocol used by the network manager.
This includes the Reservation, MemoryTimeCard, and QCap classes, which are used by the network manager to track reservations.
Also included is the definition of the message type used by the reservation protocol.
"""

from enum import Enum, auto
from math import inf
from typing import Callable, Dict, List, TYPE_CHECKING
if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..resource_management.memory_manager import MemoryInfo, MemoryManager

from ..entanglement_management.generation import EntanglementGenerationA
from ..entanglement_management.purification import BBPSSW
from ..entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from ..kernel.event import Event
from ..kernel.process import Process
from ..message import Message
from ..protocol import StackProtocol
from ..resource_management.rule_manager import Rule

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
        return "ResourceReservationProtocol: \n\ttype=%s, \n\treservation=%s" % (self.msg_type, self.reservation)


class ResourceReservationProtocol(StackProtocol):
    """ReservationProtocol for  node resources.

    The reservation protocol receives network entanglement requests and attempts to reserve local resources.
    If successful, it will forward the request to another node in the entanglement path and create local rules.
    These rules are passed to the node's resource manager.
    If unsuccessful, the protocol will notify the network manager of failure.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        timecards (List[MemoryTimeCard]): list of reservation cards for all memories on node.
        es_success_probability (float): sets `success_probability` of `EntanglementSwappingA` protocols created by rules.
        es_degredation (float): sets `degredation` of `EntanglementSwappingA` protocols created by rules.
        accepted_reservations (List[Reservation]): list of all approved reservation requests.
    """

    def __init__(self, own: "QuantumRouter", name: str):
        """Constructor for the reservation protocol class.

        Args:
            own (QuantumRouter): node to attach protocol to.
            name (str): label for reservation protocol instance.
        """

        super().__init__(own, name)
        self.timecards = [MemoryTimeCard(i) for i in range(len(own.memory_array))]
        self.es_success_probability = 1
        self.es_degradation = 0.95
        self.accepted_reservations = []

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
            msg = ResourceReservationMessage(RSVPMsgType.REJECT, self.name, reservation)
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
                    new_msg = ResourceReservationMessage(RSVPMsgType.APPROVE, self.name, msg.reservation, path=path)
                    self._pop(msg=msg)
                    self._push(dst=msg.reservation.initiator, msg=new_msg)
                else:
                    self._push(dst=msg.reservation.responder, msg=msg)
            else:
                new_msg = ResourceReservationMessage(RSVPMsgType.REJECT, self.name, msg.reservation)
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

        counter_multiple = 1 if self.own.name in [reservation.initiator, reservation.responder] else 2
        counter = counter_multiple * reservation.memory_size

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
        memory_indices = [card.memory_index for card in self.timecards if reservation in card.reservations]

        # create rules for entanglement generation
        index = path.index(self.own.name)
        if index > 0:
            def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if memory_info.state == RAW and memory_info.index in memory_indices[:reservation.memory_size]:
                    return [memory_info]
                else:
                    return []

            def eg_rule_action(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]
                memory = memories[0]
                previous_node_in_path = path[index - 1]
                middle_node = self.own.map_to_middle_node[previous_node_in_path]
                protocol = EntanglementGenerationA(None,
                                                   "EGA." + memory.name,
                                                   middle_node,
                                                   previous_node_in_path,
                                                   memory)
                return [protocol, [None], [None]]

            rule = Rule(10, eg_rule_action, eg_rule_condition)
            rules.append(rule)

        if index < len(path) - 1:
            def eg_rule_action(memories_info: List["MemoryInfo"]):
                def requirement(protocols):
                    for protocol in protocols:
                        if isinstance(protocol, EntanglementGenerationA) \
                                and protocol.other == self.own.name \
                                and protocol.rule.get_reservation() == reservation:
                            return protocol

                memories = [info.memory for info in memories_info]
                memory = memories[0]
                next_node_in_path = path[index + 1]
                middle_node = self.own.map_to_middle_node[next_node_in_path]
                protocol = EntanglementGenerationA(None,
                                                   "EGA." + memory.name,
                                                   middle_node,
                                                   next_node_in_path,
                                                   memory)
                return [protocol, [path[index + 1]], [requirement]]

            eg_rule_condition = self._eg_rule_condition_before_last_node(index, memory_indices, reservation)
            rule = Rule(10, eg_rule_action, eg_rule_condition)
            rules.append(rule)

        # create rules for entanglement purification
        if index > 0:
            def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.index in memory_indices[:reservation.memory_size]
                        and memory_info.state == ENTANGLED and memory_info.fidelity < reservation.fidelity):
                    for info in manager:
                        if (info != memory_info and info.index in memory_indices[:reservation.memory_size]
                                and info.state == ENTANGLED and info.remote_node == memory_info.remote_node
                                and info.fidelity == memory_info.fidelity):
                            assert memory_info.remote_memo != info.remote_memo
                            return [memory_info, info]
                return []

            def ep_rule_action(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]

                def requirement(protocols):
                    new_protocols = self._initialize_ep_rule_action_requirement(protocols, memories_info)

                    if len(new_protocols) != 2:
                        return None

                    self._configure_ep_rule_action_requirement(protocols, new_protocols)

                    return new_protocols[0]

                name = "EP.%s.%s" % (memories[0].name, memories[1].name)
                purification = BBPSSW(None, name, memories[0], memories[1])
                destinations = [memories_info[0].remote_node]
                requirements = [requirement]
                return purification, destinations, requirements

            rule = Rule(10, ep_rule_action, ep_rule_condition)
            rules.append(rule)

        if index < len(path) - 1:
            def ep_rule_action(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]
                name = f'EP.{memories[0].name}'
                purification = BBPSSW(None, name, memories[0], None)
                return purification, [None], [None]

            ep_rule_condition = self._ep_rule_condition_before_last_node(index, memory_indices, reservation)
            rule = Rule(10, ep_rule_action, ep_rule_condition)
            rules.append(rule)

        # create rules for entanglement swapping
        def es_rule_actionB(memories_info: List["MemoryInfo"]):
            memories = [info.memory for info in memories_info]
            memory = memories[0]
            protocol = EntanglementSwappingB(None, "ESB." + memory.name, memory)
            return [protocol, [None], [None]]

        host_indices = [0, len(path) - 1]

        if index in host_indices:
            es_rule_condition = self._get_es_rule_condition_for_host(index, path, memory_indices, reservation)
            rule = Rule(10, es_rule_actionB, es_rule_condition)
            rules.append(rule)
        else:
            adjacent_nodes = self._get_adjacent_nodes_in(path)

            def es_rule_conditionA(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if self._es_rule_condition_met_for(memory_info, memory_indices, reservation):
                    adjacent_nodes_names = adjacent_nodes.values()

                    for j, adjacent_node_name in enumerate(adjacent_nodes_names):
                        if memory_info.remote_node == adjacent_node_name:
                            opposite_adjacent_node_name = adjacent_nodes_names[(j + 1) % 2]
                            for info in manager:
                                if self._es_rule_condition_met_for(info, memory_indices, reservation) \
                                        and info.remote_node == opposite_adjacent_node_name:
                                    return [memory_info, info]

                return []

            def es_rule_actionA(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]
                requirements = self._get_es_rule_swapping_requirements(memories_info)
                memories_names = [memory.name for memory in memories]
                protocol_name = f"ESA.{'.'.join(memories_names)}"
                swapping = EntanglementSwappingA(None,
                                                 protocol_name,
                                                 memories[0],
                                                 memories[1],
                                                 success_prob=self.es_success_probability,
                                                 degradation=self.es_degradation)
                destinations = [info.remote_node for info in memories_info]

                return swapping, destinations, requirements

            rule = Rule(10, es_rule_actionA, es_rule_conditionA)
            rules.append(rule)

            def es_rule_conditionB(memory_info: "MemoryInfo", manager: "MemoryManager") -> List["MemoryInfo"]:
                if self._es_rule_condition_met_for(memory_info, memory_indices, reservation) \
                        and memory_info.remote_node not in adjacent_nodes.values():
                    return [memory_info]
                else:
                    return []

            rule = Rule(10, es_rule_actionB, es_rule_conditionB)
            rules.append(rule)

        for rule in rules:
            rule.set_reservation(reservation)
        return rules

    @staticmethod
    def _eg_rule_condition_before_last_node(own_node_path_index: int,
                                            memory_indices: List[int],
                                            reservation: "Reservation") \
            -> Callable[[MemoryInfo, MemoryManager], List[MemoryInfo]]:
        start_index = 0 if own_node_path_index == 0 else reservation.memory_size

        def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if memory_info.state == RAW and memory_info.index in memory_indices[start_index]:
                return [memory_info]
            else:
                return []

        return eg_rule_condition

    @staticmethod
    def _initialize_ep_rule_action_requirement(protocols: List, memories_info: List[MemoryInfo]) -> List:
        purification_protocols = [protocol for protocol in protocols if isinstance(protocol, BBPSSW)]

        new_protocols = []
        for protocol in purification_protocols:
            for j, memory_info in enumerate(memories_info):
                if protocol.kept_memo.name == memory_info.remote_memo:
                    new_protocols.insert(j, protocol)

        return new_protocols

    @staticmethod
    def _configure_ep_rule_action_requirement(original_protocols, new_protocols) -> None:
        original_protocols.remove(new_protocols[1])
        new_protocols[1].rule.protocols.remove(new_protocols[1])
        new_protocols[1].kept_memo.detach(new_protocols[1])
        new_protocols[0].meas_memo = new_protocols[1].kept_memo
        new_protocols[0].memories = [new_protocols[0].kept_memo, new_protocols[0].meas_memo]
        new_protocols[0].name = new_protocols[0].name + "." + new_protocols[0].meas_memo.name
        new_protocols[0].meas_memo.attach(new_protocols[0])
        new_protocols[0].t0 = new_protocols[0].kept_memo.timeline.now()

    def _get_es_rule_condition_for_host(self,
                                        index: int,
                                        path: List[str],
                                        memory_indices: List[int],
                                        reservation: "Reservation") \
            -> Callable[[MemoryInfo, MemoryManager], List[MemoryInfo]]:
        other_host = path[-1 if index == 0 else 0]

        def es_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if self._es_rule_condition_met_for(memory_info, memory_indices, reservation) \
                    and memory_info.remote_node != other_host:
                return [memory_info]
            else:
                return []

        return es_rule_condition

    @staticmethod
    def _ep_rule_condition_before_last_node(own_node_path_index: int,
                                            memory_indices: List[int],
                                            reservation: "Reservation") -> Callable[[MemoryInfo], List[MemoryInfo]]:
        start_index = 0 if own_node_path_index == 0 else reservation.memory_size

        def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
            if (memory_info.index in memory_indices[start_index:]
                    and memory_info.state == ENTANGLED and memory_info.fidelity < reservation.fidelity):
                return [memory_info]
            return []

        return ep_rule_condition

    def _get_adjacent_nodes_in(self, path: List[str]) -> Dict:
        _path = path[:]

        while _path.index(self.own.name) % 2 == 0:
            _path = [node_name for i, node_name in enumerate(_path) if i % 2 == 0 or i == len(path) - 1]

        own_node_path_index = _path.index(self.own.name)

        return {'left': _path[own_node_path_index - 1], 'right': _path[own_node_path_index + 1]}

    @staticmethod
    def _es_rule_condition_met_for(memory_info: "MemoryInfo",
                                  memory_indices: List[int],
                                  reservation: "Reservation") -> bool:
        return memory_info.state == ENTANGLED \
               and memory_info.index in memory_indices \
               and memory_info.fidelity >= reservation.fidelity

    @staticmethod
    def _get_es_rule_swapping_requirements(memories_info: List[MemoryInfo]) -> List[Callable]:
        requirements = []

        for memory_info in memories_info[:2]:
            def requirement(protocols):
                for protocol in protocols:
                    if isinstance(protocol, EntanglementSwappingB) \
                            and protocol.memory.name == memory_info.remote_memo:
                        return protocol

            requirements.append(requirement)

        return requirements

    def load_rules(self, rules: List["Rule"], reservation: "Reservation") -> None:
        """Method to add created rules to resource manager.

        This method will schedule the resource manager to load all rules at the reservation start time.
        The rules will be set to expire at the reservation end time.

        Args:
            rules (List[Rules]): rules to add.
            reservation (Reservation): reservation that created the rules.
        """

        self.accepted_reservations.append(reservation)

        for card in self.timecards:
            if reservation in card.reservations:
                activation_arguments = [None, self.own.memory_array[card.memory_index], RAW]
                activation_method = 'update'
                self._schedule_event(reservation, activation_method, activation_arguments)

        for rule in rules:
            activation_arguments = [rule]
            for activation_method in ('load', 'expire'):
                self._schedule_event(reservation, activation_method, activation_arguments)

    def _schedule_event(self, reservation: "Reservation", activation_method: str, activation_arguments: List) -> None:
        activations = {
            'load': {'priority': inf, 'time': reservation.start_time},
            'expire': {'priority': 0, 'time': reservation.end_time},
            'update': {'priority': 1, 'time': reservation.start_time}
        }

        priority = activations[activation_method]['priority']
        reservation_time = activations[activation_method]['time']

        process = Process(self.own.resource_manager, activation_method, activation_arguments)
        event = Event(reservation_time, process, priority)

        self.own.timeline.schedule(event)

    def received_message(self, src, msg):
        """Method to receive messages directly (should not be used; receive through network manager)."""

        raise Exception("RSVP protocol should not call this function")

    def set_swapping_success_rate(self, probability: float) -> None:
        assert 0 <= probability <= 1
        self.es_success_probability = probability

    def set_swapping_degradation(self, degradation: float) -> None:
        assert 0 <= degradation <= 1
        self.es_degradation = degradation


class Reservation():
    """Tracking of reservation parameters for the network manager.

    Attributes:
        initiator (str): name of the node that created the reservation request.
        responder (str): name of distant node with witch entanglement is requested.
        start_time (int): simulation time at which entanglement should be attempted.
        end_time (int): simulation time at which resources may be released.
        memory_size (int): number of entangled memory pairs requested.
    """

    def __init__(self, initiator: str, responder: str, start_time: int, end_time: int, memory_size: int,
                 fidelity: float):
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
        assert self.start_time < self.end_time
        assert self.memory_size > 0

    def __str__(self):
        reservation_parameters = {
            'initiator': self.initiator,
            'responder': self.responder,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'memory_size': self.memory_size,
            'target_fidelity': f'{self.fidelity:.2f}'
        }

        formatted_parameters_string = ', '.join([f'{parameter}={value}'
                                                 for parameter, value in reservation_parameters.items()])

        return f'Reservation: {formatted_parameters_string}'


class MemoryTimeCard():
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
            middle = (start + end) // 2
            if self.reservations[middle].start_time > reservation.end_time:
                end = middle - 1
            elif self.reservations[middle].end_time < reservation.start_time:
                start = middle + 1
            elif max(self.reservations[middle].start_time, reservation.start_time) <= \
                    min(self.reservations[middle].end_time, reservation.end_time):
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
