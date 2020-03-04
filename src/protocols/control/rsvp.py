import math
from abc import ABC
from typing import List, Dict

from protocols import Protocol

from sequence import topology
from sequence.process import Process
from sequence.event import Event
from protocols import EntanglementGeneration, BBPSSW, EntanglementSwapping, EndProtocol, Protocol


class ResourceReservationProtocol(Protocol):
    def __init__(self, own):
        if own is None:
            return
        Protocol.__init__(self, own)
        self.reservation = []

    def request(self, responder: str, fidelity: float, memory_size: int, start_time: int, end_time: int):
        msg = ResourceReservationMessage(msg_type="REQUEST")
        msg.initiator = self.own.name
        msg.responder = responder
        msg.fidelity = fidelity
        msg.memory_size = memory_size
        msg.start_time = start_time
        msg.end_time = end_time

        memories = self.handle_request(msg)
        if memories:
            qcap = QCap(self.own, None, memories)
            msg.qcaps.append(qcap)
            # print(self.own.timeline.now() / 1e12, self.own.name, "RSVP request", msg)
            self._push(msg=msg, dst=responder)

    def push(self):
        pass

    def pop(self, msg: ResourceReservationMessage, src: str):
        # print("   RSVP pop is called, src: ", src, "msg:", msg)
        if msg.msg_type == "REQUEST":
            assert msg.start_time > self.own.timeline.now()
            memories = self.handle_request(msg)
            if memories:
                pre_node = msg.qcaps[-1].node
                qcap = QCap(self.own, self.own.middles[pre_node.name], memories)
                msg.qcaps.append(qcap)
                if self.own.name != msg.responder:
                    self._push(msg=msg, dst=msg.responder)
                else:
                    self._pop(msg=msg)
                    resp_msg = ResourceReservationMessage("RESPONSE")
                    resp_msg.initiator = msg.initiator
                    resp_msg.responder = msg.responder
                    resp_msg.start_time = msg.start_time
                    resp_msg.end_time = msg.end_time
                    rulesets = self.create_rulesets(msg)
                    self.load_ruleset(rulesets.pop())
                    resp_msg.rulesets = rulesets
                    self._push(msg=resp_msg, dst=msg.initiator)
                    print("   msg arrives dst", self.own.name, "; msg is ", msg)
            else:
                rej_msg = ResourceReservationMessage("REJECT")
                rej_msg.initiator = msg.initiator
                rej_msg.responder = msg.responder
                rej_msg.start_time = msg.start_time
                rej_msg.end_time = msg.end_time
                self._push(msg=rej_msg, dst=msg.initiator)
        elif msg.msg_type == "REJECT":
            resv = Reservation(msg.initiator, msg.responder, msg.start_time, msg.end_time)
            self.remove_reservation(resv)
            if self.own.name != msg.initiator:
                self._push(msg=msg, dst=msg.initiator)
            else:
                # print("   REJECT: msg arrives src", self.own.name, "; request is ", msg)
                self._pop(msg=msg)
        elif msg.msg_type == "RESPONSE":
            ruleset = msg.rulesets.pop()
            self.load_ruleset(ruleset)
            if self.own.name != msg.initiator:
                self._push(msg=msg, dst=msg.initiator)
            else:
                self._pop(msg=msg)
                # print("   RESPONSE: msg arrives src", self.own.name, "; response is ", msg)

    def handle_request(self, msg) -> int:
        '''
        return 0 : request is rejected
        return 1 : request is approved
        '''
        def schedule_reservation(resv: Reservation, reservations: List[Reservation]) -> int:
            start, end = 0, len(reservations) - 1
            while start <= end:
                mid = (start + end) // 2
                if reservations[mid].start_time > resv.end_time:
                    end = mid - 1
                elif reservations[mid].end_time < resv.start_time:
                    start = mid + 1
                elif max(reservations[mid].start_time, resv.start_time) < min(reservations[mid].end_time, resv.end_time):
                    return -1
                else:
                    print(resv)
                    for r in reservations:
                        print(r)
                    raise Exception("Unexpected status")
            return start

        resv = Reservation(msg.initiator, msg.responder, msg.start_time, msg.end_time)
        if self.own.name == msg.initiator or self.own.name == msg.responder:
            counter = msg.memory_size
        else:
            counter = msg.memory_size * 2
        memories = []

        for i, reservations in enumerate(self.reservation):
            pos = schedule_reservation(resv, reservations)
            if pos != -1:
                memories.append([i, pos])
                counter -= 1

            if counter == 0:
                break

        if counter > 0:
            return []

        indices = []
        for i, pos in memories:
            self.reservation[i].insert(pos, resv)
            indices.append(i)

        return indices

    def remove_reservation(self, resv):
        for reservations in self.reservation:
            if resv in reservations:
                reservations.remove(resv)

    def create_rulesets(self, msg):
        end_nodes = []
        mid_nodes = []
        memories = []
        reservation = Reservation(msg.initiator, msg.responder, msg.start_time, msg.end_time)
        for i, qcap in enumerate(msg.qcaps):
            end_nodes.append(qcap.node)
            if i != 0:
                mid_nodes.append(qcap.mid_node)
            memories.append(qcap.memories)

        create_action(end_nodes, mid_nodes,  memories, msg.fidelity, reservation)

        return [None] * len(msg.qcaps)

    def load_ruleset(self, ruleset):
        return 0

    def received_message(self, src, msg):
        raise Exception("RSVP protocol should not call this function")

    def init(self):
        memory_array = self.own.components['MemoryArray']
        for memory in memory_array:
            self.reservation.append([])

