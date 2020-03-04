import math
from typing import List

from ..entanglement.purification import BBPSSW
from ..entanglement.swapping import EntanglementSwapping
from ..entanglement.utils import EndProtocol
from ..message import Message
from ..protocol import Protocol
from ...components.optical_channel import ClassicalChannel
from ...kernel.event import Event
from ...kernel.process import Process


class ResourceReservationMessage(Message):
    def __init__(self, msg_type: str):
        Message.__init__(self, msg_type)
        self.owner_type = type(ResourceReservationProtocol(None))
        self.responder = None
        self.initiator = None
        self.start_time = None
        self.end_time = None
        if self.msg_type == "REQUEST":
            self.fidelity = None
            self.memory_size = None
            self.qcaps = []
        elif self.msg_type == "REJECT":
            pass
        elif self.msg_type == "RESPONSE":
            self.rulesets = None
        else:
            raise Exception("Unknown type of message")

    def __str__(self):
        common = "ResourceReservationProtocol: \n\ttype=%s, \n\tinitiator=%s, \n\tresponder=%s, \n\tstart time=%d, \n\tend time=%d" % (
            self.msg_type, self.initiator, self.responder, self.start_time, self.end_time)
        if self.msg_type == "REQUEST":
            return common + ("\n\tfidelity=%.2f, \n\tmemory_size=%d, \n\tqcaps length=%s" % (
                self.fidelity, self.memory_size, len(self.qcaps)))
        elif self.msg_type == "REJECT":
            return common
        elif self.msg_type == "RESPONSE":
            return common + ("\n\trulesets=%s" % self.rulesets)


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


class Reservation():
    def __init__(self, initiator, responder, start_time, end_time):
        self.initiator = initiator
        self.responder = responder
        self.start_time = start_time
        self.end_time = end_time

    def __eq__(self, another):
        return (self.initiator == another.initiator and
                self.responder == another.responder and
                self.start_time == another.start_time and
                self.end_time == another.end_time)

    def __str__(self):
        return "Reservation: initiator=%s, responder=%s, start_time=%d, end_time=%d" % (
            self.initiator, self.responder, self.start_time, self.end_time)


class QCap():
    def __init__(self, node, mid_node, memories):
        self.node = node
        self.mid_node = mid_node
        self.memories = memories


def create_action(end_nodes, mid_nodes, memories, fidelity, reservation, flag=True):
    '''
    n: the number of end nodes
    '''
    if flag is False:
        return

    UNIT_DELAY = 25e9
    UNIT_DISTANCE = 40000
    start_time, end_time = reservation.start_time, reservation.end_time
    n = len(end_nodes)
    rsvp_name = "%s_%s_%d_%d" % (reservation.initiator, reservation.responder, start_time, end_time)

    # create classical channels between end nodes
    for i, node1 in enumerate(end_nodes):
        for j, node2 in enumerate(end_nodes):
            if i >= j or node2.name in node1.cchannels:
                continue
            delay = (j - i) * 2 * UNIT_DELAY
            name = "cc_%s_%s" % (node1.name, node2.name)
            distance = (j - i) * 2 * UNIT_DISTANCE
            cc = ClassicalChannel(name, node1.timeline, distance=distance, delay=delay)
            cc.set_ends([node1, node2])
            # print('add', name, 'to', node1.name)
            # print('add', name, 'to', node2.name)

    for node in end_nodes:
        # print(node.name)
        for dst in node.cchannels:
            cchannel = node.cchannels[dst]
            # print("    ", dst, cchannel.name, cchannel.ends[0].name, '<->', cchannel.ends[1].name)

    # schedule setting of memory.direct_receiver
    for i, node in enumerate(end_nodes):
        if i > 0:
            mid_node = mid_nodes[i - 1]
            qc = node.qchannels[mid_node.name]

            memory_array = node.components['MemoryArray']
            if i == n - 1:
                process = Process(memory_array, "set_direct_receiver", [memories[i], qc])
                event = Event(start_time, process, 1)
                node.timeline.schedule(event)
                process = Process(node.eg_protocol, "add_memories", [memories[i], qc, end_time])
                event = Event(start_time, process, 3)
                node.timeline.schedule(event)
            else:
                length = len(memories[i])
                process = Process(memory_array, "set_direct_receiver", [memories[i][:length // 2], qc])
                event = Event(start_time, process, 1)
                node.timeline.schedule(event)
                process = Process(node.eg_protocol, "add_memories", [memories[i][:length // 2], qc, end_time])
                event = Event(start_time, process, 3)
                node.timeline.schedule(event)

        if i < len(mid_nodes):
            mid_node = mid_nodes[i]
            qc = node.qchannels[mid_node.name]

            memory_array = node.components['MemoryArray']
            if i == 0:
                process = Process(memory_array, "set_direct_receiver", [memories[i], qc])
                event = Event(start_time, process, 1)
                node.timeline.schedule(event)
                process = Process(node.eg_protocol, "add_memories", [memories[i], qc, end_time])
                event = Event(start_time, process, 3)
                node.timeline.schedule(event)
            else:
                length = len(memories[i])
                process = Process(memory_array, "set_direct_receiver", [memories[i][length // 2:], qc])
                event = Event(start_time, process, 1)
                node.timeline.schedule(event)
                process = Process(node.eg_protocol, "add_memories", [memories[i][length // 2:], qc, end_time])
                event = Event(start_time, process, 3)
                node.timeline.schedule(event)

    for i, node in enumerate(end_nodes):
        process = Process(node.eg_protocol, "remove_memories", [memories[i]])
        event = Event(start_time, process, 2)
        node.timeline.schedule(event)

    '''
    for node in end_nodes:
        print(node.name)
        for dst in node.qchannels:
            qc = node.qchannels[dst]
            print("    ", dst, qc.sender.name, "->", qc.receiver.name)
    '''

    # create end nodes purification protocols
    for i, node in enumerate(end_nodes):
        bbpssw = BBPSSW(node, threshold=fidelity)

        middles = []
        others = []
        if i > 0:
            middles.append(mid_nodes[i - 1].name)
            others.append(end_nodes[i - 1].name)
        if i + 1 < len(end_nodes):
            middles.append(mid_nodes[i].name)
            others.append(end_nodes[i + 1].name)

        eg = node.eg_protocol
        if i % 2 == 1:
            eg.is_start = True  # set "is_start" to true on every other node
        eg.upper_protocols.append(bbpssw)
        bbpssw.lower_protocols.append(eg)

        node.protocols.append(node.protocols.pop(0))

    def add_protocols(node, name1, name2):
        top_protocol = node.protocols[-1]
        es = EntanglementSwapping(node, name1, name2, [])
        top_protocol.upper_protocols.append(es)
        es.lower_protocols.append(top_protocol)
        ep = BBPSSW(node, threshold=fidelity)
        ep.lower_protocols.append(es)
        es.upper_protocols.append(ep)

    def create_stack(left, right, end_nodes):
        assert int(math.log2(right - left)) == math.log2(right - left)
        k = 1
        while k <= (right - left) / 2:
            m = 0
            pos = k * (2 * m + 1) + left
            while pos + k <= right:
                remote1, remote2 = pos - k, pos + k
                if remote1 == 0:
                    node = end_nodes[remote1]
                    add_protocols(node, '', '')

                node = end_nodes[pos]
                add_protocols(node, end_nodes[remote1].name, end_nodes[remote2].name)

                node = end_nodes[remote2]
                add_protocols(node, '', '')

                m += 1
                pos = k * (2 * m + 1) + left
            k *= 2

    # create end nodes purification and swapping protocols
    left, right = 0, n - 1
    while right - left > 1:
        length = 2 ** int(math.log2(right - left))
        create_stack(left, left + length, end_nodes)
        left = left + length
        if left != right:
            next_length = 2 ** int(math.log2(right - left))
            add_protocols(end_nodes[left], end_nodes[0].name, end_nodes[left + next_length].name)
            add_protocols(end_nodes[0], '', '')
            add_protocols(end_nodes[left + next_length], '', '')

    # update known_nodes for EntanglementSwapping protocols
    for i, node in enumerate(end_nodes):
        ess = [protocol for protocol in node.protocols if type(protocol).__name__ == "EntanglementSwapping"]
        counter = 0
        for j in range(i - 1, -1, -1):
            node2 = end_nodes[j]
            ess2 = [protocol for protocol in node2.protocols if type(protocol).__name__ == "EntanglementSwapping"]
            for es in ess2:
                if es.remote2 == node.name:
                    ess[counter].known_nodes.append(node2.name)
                    counter += 1
        counter = 0
        for j in range(i + 1, len(end_nodes)):
            node2 = end_nodes[j]
            ess2 = [protocol for protocol in node2.protocols if type(protocol).__name__ == "EntanglementSwapping"]
            for es in ess2:
                if es.remote1 == node.name:
                    ess[counter].known_nodes.append(node2.name)
                    counter += 1

    '''
    for node in end_nodes:
        print(node.name)
        for protocol in node.protocols:
            print("    ", protocol)
            print(" "*8, "upper protocols", protocol.upper_protocols)
            print(" "*8, "lower protocols", protocol.lower_protocols)
    '''

    # schedule start events
    for node in end_nodes:
        process = Process(node.eg_protocol, "start", [])
        event = Event(start_time, process)
        node.timeline.schedule(event)

    for i, node in enumerate(end_nodes):
        for protocol in node.protocols:
            process = Process(protocol, "set_valid_memories", [memories[i]])
            event = Event(start_time, process)
            node.timeline.schedule(event)

    # schedule end events
    for node in end_nodes:
        process = Process(node, "remove_action", [rsvp_name])
        event = Event(end_time, process)
        node.timeline.schedule(event)

    # create EndProtocol on the first and last nodes
    cur_last = end_nodes[0].protocols[-1]
    endprotocol = EndProtocol(end_nodes[0])
    endprotocol.lower_protocols.append(cur_last)
    cur_last.upper_protocols.append(endprotocol)

    cur_last = end_nodes[-1].protocols[-1]
    endprotocol = EndProtocol(end_nodes[-1])
    endprotocol.lower_protocols.append(cur_last)
    cur_last.upper_protocols.append(endprotocol)

    # move self.protocols to self.action_cluster
    for node in end_nodes:
        for protocol in node.protocols:
            protocol.rsvp_name = rsvp_name
        node.action_cluster[rsvp_name] = node.protocols
        node.protocols = []

    for node in mid_nodes:
        for protocol in node.protocols:
            protocol.rsvp_name = 'MID'
