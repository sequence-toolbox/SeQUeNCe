from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...topology.node import QuantumRouter
    from ..management.memory_manager import MemoryInfo, MemoryManager

from ..management.rule_manager import Rule
from ..entanglement.generation import EntanglementGenerationA
from ..entanglement.purification import BBPSSW
from ..entanglement.swapping import EntanglementSwappingA, EntanglementSwappingB
from ..message import Message
from ..protocol import StackProtocol
from ...kernel.event import Event
from ...kernel.process import Process


class ResourceReservationMessage(Message):
    def __init__(self, msg_type: str, receiver: str, reservation: "Reservation", **kwargs):
        Message.__init__(self, msg_type, receiver)
        self.reservation = reservation
        if self.msg_type == "REQUEST":
            self.qcaps = []
        elif self.msg_type == "REJECT":
            pass
        elif self.msg_type == "APPROVE":
            self.path = kwargs["path"]
        else:
            raise Exception("Unknown type of message")

    def __str__(self):
        return "ResourceReservationProtocol: \n\ttype=%s, \n\treservation=%s" % (self.msg_type, self.reservation)


class ResourceReservationProtocol(StackProtocol):
    def __init__(self, own: "QuantumRouter", name: str):
        super().__init__(own, name)
        self.timecards = [MemoryTimeCard(i) for i in range(len(own.memory_array))]

    def push(self, responder: str, start_time: int, end_time: int, memory_size: int, target_fidelity: float):
        reservation = Reservation(self.own.name, responder, start_time, end_time, memory_size, target_fidelity)
        if self.schedule(reservation):
            msg = ResourceReservationMessage("REQUEST", self.name, reservation)
            qcap = QCap(self.own.name)
            msg.qcaps.append(qcap)
            self._push(dst=responder, msg=msg)
        else:
            msg = ResourceReservationMessage("REJECT", self.name, reservation)
            self._pop(msg=msg)

    def pop(self, src: str, msg: "ResourceReservationMessage"):
        if msg.msg_type == "REQUEST":
            if self.schedule(msg.reservation):
                qcap = QCap(self.own.name)
                msg.qcaps.append(qcap)
                if self.own.name == msg.reservation.responder:
                    path = [qcap.node for qcap in msg.qcaps]
                    rules = self.create_rules(path, reservation=msg.reservation)
                    self.load_rules(rules, msg.reservation)
                    new_msg = ResourceReservationMessage("APPROVE", self.name, msg.reservation, path=path)
                    self._push(dst=msg.reservation.initiator, msg=new_msg)
                else:
                    self._push(dst=msg.reservation.responder, msg=msg)
            else:
                new_msg = ResourceReservationMessage("REJECT", self.name, msg.reservation)
                self._push(dst=msg.reservation.initiator, msg=new_msg)
        elif msg.msg_type == "REJECT":
            for card in self.timecards:
                card.remove(msg.reservation)
            if msg.reservation.initiator == self.own.name:
                self._pop(msg=msg)
            else:
                self._push(dst=msg.reservation.initiator, msg=msg)
        elif msg.msg_type == "APPROVE":
            rules = self.create_rules(msg.path, msg.reservation)
            self.load_rules(rules, msg.reservation)
            if msg.reservation.initiator == self.own.name:
                self._pop(msg=msg)
            else:
                self._push(dst=msg.reservation.initiator, msg=msg)
        else:
            raise Exception("Unknown type of message", msg.msg_type)

    def schedule(self, reservation: "Reservation") -> bool:
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
        rules = []
        memory_indices = []
        for card in self.timecards:
            if reservation in card.reservations:
                memory_indices.append(card.memory_index)

        # create rules for entanglement generation
        index = path.index(self.own.name)
        if index > 0:
            def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if memory_info.state == "RAW" and memory_info.index in memory_indices[:reservation.memory_size]:
                    return [memory_info]
                else:
                    return []

            def eg_rule_action(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]
                memory = memories[0]
                mid = self.own.map_to_middle_node[path[index - 1]]
                protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid, path[index - 1], memory)
                return [protocol, [None], [None]]

            rule = Rule(10, eg_rule_action, eg_rule_condition)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                    if memory_info.state == "RAW" and memory_info.index in memory_indices:
                        return [memory_info]
                    else:
                        return []
            else:
                def eg_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                    if memory_info.state == "RAW" and memory_info.index in memory_indices[reservation.memory_size:]:
                        return [memory_info]
                    else:
                        return []

            def eg_rule_action(memories_info: List["MemoryInfo"]):
                def req_func(protocols):
                    for protocol in protocols:
                        if isinstance(protocol, EntanglementGenerationA) and protocol.other == self.own.name:
                            return protocol

                memories = [info.memory for info in memories_info]
                memory = memories[0]
                mid = self.own.map_to_middle_node[path[index + 1]]
                protocol = EntanglementGenerationA(None, "EGA." + memory.name, mid, path[index + 1], memory)
                protocol.primary = True
                return [protocol, [path[index + 1]], [req_func]]

            rule = Rule(10, eg_rule_action, eg_rule_condition)
            rules.append(rule)

        # create rules for entanglement purification
        if index > 0:
            def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.index in memory_indices[:reservation.memory_size]
                        and memory_info.state == "ENTANGLED" and memory_info.fidelity < reservation.fidelity):
                    for info in manager:
                        if (info != memory_info and info.index in memory_indices[:reservation.memory_size]
                                and info.state == "ENTANGLED" and info.remote_node == memory_info.remote_node
                                and info.fidelity == memory_info.fidelity):
                            return [memory_info, info]
                return []

            def ep_rule_action(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]

                def req_func(protocols):
                    _protocols = []
                    for protocol in protocols:
                        if not isinstance(protocol, BBPSSW):
                            continue

                        if protocol.kept_memo.name == memories_info[0].remote_memo:
                            _protocols.insert(0, protocol)
                        if protocol.kept_memo.name == memories_info[1].remote_memo:
                            _protocols.insert(1, protocol)

                    if len(_protocols) != 2:
                        return None

                    _protocols[0].meas_memo = _protocols[1].kept_memo
                    _protocols[0].memories = [_protocols[0].kept_memo, _protocols[0].meas_memo]
                    _protocols[0].name = _protocols[0].name + "." + _protocols[0].meas_memo.name
                    protocols.remove(_protocols[1])
                    _protocols[1].rule.protocols.remove(_protocols[1])

                    return _protocols[0]

                name = "EP.%s.%s" % (memories[0].name, memories[1].name)
                protocol = BBPSSW(None, name, memories[0], memories[1])
                dsts = [memories_info[0].remote_node]
                req_funcs = [req_func]
                return protocol, dsts, req_funcs

            rule = Rule(10, ep_rule_action, ep_rule_condition)
            rules.append(rule)

        if index < len(path) - 1:
            if index == 0:
                def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                    if (memory_info.index in memory_indices
                            and memory_info.state == "ENTANGLED" and memory_info.fidelity < reservation.fidelity):
                        return [memory_info]
                    return []
            else:
                def ep_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                    if (memory_info.index in memory_indices[reservation.memory_size:]
                            and memory_info.state == "ENTANGLED" and memory_info.fidelity < reservation.fidelity):
                        return [memory_info]
                    return []

            def ep_rule_action(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]
                name = "EP.%s" % (memories[0].name)
                protocol = BBPSSW(None, name, memories[0], None)
                return protocol, [None], [None]

            rule = Rule(10, ep_rule_action, ep_rule_condition)
            rules.append(rule)

        # create rules for entanglement swapping
        def es_rule_actionB(memories_info: List["MemoryInfo"]):
            memories = [info.memory for info in memories_info]
            memory = memories[0]
            protocol = EntanglementSwappingB(None, "ESB." + memory.name, memory)
            return [protocol, [None], [None]]

        if index == 0:
            def es_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.state == "ENTANGLED"
                        and memory_info.index in memory_indices
                        and memory_info.remote_node != path[-1]
                        and memory_info.fidelity >= reservation.fidelity):
                    return [memory_info]
                else:
                    return []

            rule = Rule(10, es_rule_actionB, es_rule_condition)
            rules.append(rule)

        elif index == len(path) - 1:
            def es_rule_condition(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.state == "ENTANGLED"
                        and memory_info.index in memory_indices
                        and memory_info.remote_node != path[0]
                        and memory_info.fidelity >= reservation.fidelity):
                    return [memory_info]
                else:
                    return []

            rule = Rule(10, es_rule_actionB, es_rule_condition)
            rules.append(rule)

        else:
            _path = path[:]
            while _path.index(self.own.name) % 2 == 0:
                new_path = []
                for i, n in enumerate(_path):
                    if i % 2 == 0 or i == len(path) - 1:
                        new_path.append(n)
                _path = new_path
            _index = _path.index(self.own.name)
            left, right = _path[_index - 1], _path[_index + 1]

            def es_rule_conditionA(memory_info: "MemoryInfo", manager: "MemoryManager"):
                if (memory_info.state == "ENTANGLED"
                        and memory_info.index in memory_indices
                        and memory_info.remote_node == left
                        and memory_info.fidelity >= reservation.fidelity):
                    for info in manager:
                        if (info.state == "ENTANGLED"
                                and memory_info.index in memory_indices
                                and info.remote_node == right
                                and info.fidelity >= reservation.fidelity):
                            return [memory_info, info]
                elif (memory_info.state == "ENTANGLED"
                      and memory_info.index in memory_indices
                      and memory_info.remote_node == right
                      and memory_info.fidelity >= reservation.fidelity):
                    for info in manager:
                        if (info.state == "ENTANGLED"
                                and memory_info.index in memory_indices
                                and info.remote_node == left
                                and info.fidelity >= reservation.fidelity):
                            return [memory_info, info]
                return []

            def es_rule_actionA(memories_info: List["MemoryInfo"]):
                memories = [info.memory for info in memories_info]

                def req_func1(protocols):
                    for protocol in protocols:
                        if (isinstance(protocol, EntanglementSwappingB)
                                and protocol.memory.name == memories_info[0].remote_memo):
                            return protocol

                def req_func2(protocols):
                    for protocol in protocols:
                        if (isinstance(protocol, EntanglementSwappingB)
                                and protocol.memory.name == memories_info[1].remote_memo):
                            return protocol

                protocol = EntanglementSwappingA(None, "ESA.%s.%s" % (memories[0].name, memories[1].name), memories[0],
                                                 memories[1])
                dsts = [info.remote_node for info in memories_info]
                req_funcs = [req_func1, req_func2]
                return protocol, dsts, req_funcs

            rule = Rule(10, es_rule_actionA, es_rule_conditionA)
            rules.append(rule)

            def es_rule_conditionB(memory_info: "MemoryInfo", manager: "MemoryManager") -> List["MemoryInfo"]:
                if (memory_info.state == "ENTANGLED"
                        and memory_info.index in memory_indices
                        and memory_info.remote_node not in [left, right]
                        and memory_info.fidelity >= reservation.fidelity):
                    return [memory_info]
                else:
                    return []

            rule = Rule(10, es_rule_actionB, es_rule_conditionB)
            rules.append(rule)

        return rules

    def load_rules(self, rules: List["Rule"], reservation: "Reservation") -> None:
        for rule in rules:
            process = Process(self.own.resource_manager, "load", [rule])
            event = Event(reservation.start_time, process)
            self.own.timeline.schedule(event)
            process = Process(self.own.resource_manager, "expire", [rule])
            event = Event(reservation.end_time, process)
            self.own.timeline.schedule(event)

    def received_message(self, src, msg):
        raise Exception("RSVP protocol should not call this function")


class Reservation():
    def __init__(self, initiator: str, responder: str, start_time: int, end_time: int, memory_size: int,
                 fidelity: float):
        self.initiator = initiator
        self.responder = responder
        self.start_time = start_time
        self.end_time = end_time
        self.memory_size = memory_size
        self.fidelity = fidelity
        assert self.start_time < self.end_time
        assert self.memory_size > 0

    def __str__(self):
        return "Reservation: initiator=%s, responder=%s, start_time=%d, end_time=%d, memory_size=%d, target_fidelity=%.2f" % (
            self.initiator, self.responder, self.start_time, self.end_time, self.memory_size, self.fidelity)


class MemoryTimeCard():
    def __init__(self, memory_index: int):
        self.memory_index = memory_index
        self.reservations = []

    def add(self, reservation: "Reservation") -> bool:
        pos = self.schedule_reservation(reservation)
        if pos >= 0:
            self.reservations.insert(pos, reservation)
            return True
        else:
            return False

    def remove(self, reservation: "Reservation") -> bool:
        try:
            pos = self.reservations.index(reservation)
            self.reservations.pop(pos)
            return True
        except ValueError:
            return False

    def schedule_reservation(self, resv: "Reservation") -> int:
        start, end = 0, len(self.reservations) - 1
        while start <= end:
            mid = (start + end) // 2
            if self.reservations[mid].start_time > resv.end_time:
                end = mid - 1
            elif self.reservations[mid].end_time < resv.start_time:
                start = mid + 1
            elif max(self.reservations[mid].start_time, resv.start_time) <= min(self.reservations[mid].end_time,
                                                                                resv.end_time):
                return -1
            else:
                raise Exception("Unexpected status")
        return start


class QCap():
    def __init__(self, node: str):
        self.node = node
