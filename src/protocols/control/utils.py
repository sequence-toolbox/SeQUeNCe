import math
from abc import ABC
from typing import List, Dict

from protocols import Protocol

from sequence import topology
from sequence.process import Process
from sequence.event import Event
from protocols import EntanglementGeneration, BBPSSW, EntanglementSwapping, EndProtocol, Protocol


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
        return "Reservation: initiator=%s, responder=%s, start_time=%d, end_time=%d" % (self.initiator, self.responder, self.start_time, self.end_time)


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
            cc = topology.ClassicalChannel(name, node1.timeline, distance=distance, delay=delay)
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
            mid_node = mid_nodes[i-1]
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
                process = Process(memory_array, "set_direct_receiver", [memories[i][:length//2], qc])
                event = Event(start_time, process, 1)
                node.timeline.schedule(event)
                process = Process(node.eg_protocol, "add_memories", [memories[i][:length//2], qc, end_time])
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
                process = Process(memory_array, "set_direct_receiver", [memories[i][length//2:], qc])
                event = Event(start_time, process, 1)
                node.timeline.schedule(event)
                process = Process(node.eg_protocol, "add_memories", [memories[i][length//2:], qc, end_time])
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
            middles.append(mid_nodes[i-1].name)
            others.append(end_nodes[i-1].name)
        if i + 1 < len(end_nodes):
            middles.append(mid_nodes[i].name)
            others.append(end_nodes[i+1].name)

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
        for j in range(i-1, -1, -1):
            node2 = end_nodes[j]
            ess2 = [protocol for protocol in node2.protocols if type(protocol).__name__ == "EntanglementSwapping"]
            for es in ess2:
                if es.remote2 == node.name:
                    ess[counter].known_nodes.append(node2.name)
                    counter += 1
        counter = 0
        for j in range(i+1, len(end_nodes)):
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


if __name__ == "__main__":
    from sequence.topology import Node
    from sequence import timeline

    class QuantumRouter(Node):
        def __init__(self, name, timeline, **kwargs):
            Node.__init__(self, name, timeline, **kwargs)
            self.control_protocols = []

        def append_control_protocol(self, protocol):
            if self.control_protocols:
                protocol.lower_protocols.append(self.control_protocols[-1])
                self.control_protocols[-1].upper_protocols.append(protocol)
            self.control_protocols.append(protocol)

        def receive_message(self, src: str, msg: Message):
            for protocol in self.control_protocols:
                if msg.owner_type == type(protocol):
                    protocol.received_message(src, msg)
                    return
            raise Exception("Unknown type of message")

    MEMO_ARR_SIZE = 100
    MEMO_FIDELITY = 0.8
    MEMO_EFFICIENCY = 0.5
    MEMO_ARR_FREQ = int(1e6)

    tl = timeline.Timeline()
    cqx_topo = {'WM': {'SL': 241, 'FNL': 202},
                'SL': {'WM': 241, 'FNL': 66, 'ANL': 42, 'UIUC': 222, 'UC': 15, 'NU': 20},
                'NU': {'SL': 20, 'UC': 33},
                'UC': {'SL': 15, 'NU': 33},
                'FNL': {'WM': 202, 'SL': 66, 'ANL': 48},
                'ANL': {'FNL': 48, 'UIUC': 206, 'SL': 42},
                'UIUC': {'ANL': 206, 'SL': 222}}

    # create nodes
    node_wm = QuantumRouter('WM', tl)
    node_sl = QuantumRouter('SL', tl)
    node_nu = QuantumRouter('NU', tl)
    node_uc = QuantumRouter('UC', tl)
    node_fnl = QuantumRouter('FNL', tl)
    node_anl = QuantumRouter('ANL', tl)
    node_uiuc = QuantumRouter('UIUC', tl)
    nodes = [node_wm, node_sl, node_nu, node_uc, node_fnl, node_anl, node_uiuc]

    # create forwarding table
    def create_forwarding_table(topo, node):
        # TODO: use graph algorithm to calculate forwarding table
        if node.name == 'WM':
            return {'SL': 'SL', 'NU': 'SL', 'UC': 'SL',
                    'FNL': 'FNL', 'ANL': 'FNL', 'UIUC': 'FNL'}
        elif node.name == 'SL':
            return {'WM': 'WM', 'NU': 'NU', 'UC': 'UC',
                    'FNL': 'FNL', 'ANL': 'ANL', 'UIUC': 'UIUC'}
        elif node.name == 'NU':
            return {'WM': 'SL', 'SL': 'SL', 'UC': 'UC',
                    'FNL': 'SL', 'ANL': 'SL', 'UIUC': 'SL'}
        elif node.name == 'UC':
            return {'WM': 'SL', 'SL': 'SL', 'NU': 'NU',
                    'FNL': 'SL', 'ANL': 'SL', 'UIUC': 'SL'}
        elif node.name == 'FNL':
            return {'WM': 'WM', 'SL': 'SL', 'NU': 'SL',
                    'UC': 'SL', 'ANL': 'ANL', 'UIUC': 'ANL'}
        elif node.name == 'ANL':
            return {'WM': 'FNL', 'SL': 'SL', 'NU': 'SL',
                    'UC': 'SL', 'FNL': 'FNL', 'UIUC': 'UIUC'}
        elif node.name == 'UIUC':
            return {'WM': 'ANL', 'SL': 'SL', 'NU': 'SL',
                    'UC': 'SL', 'FNL': 'ANL', 'ANL': 'ANL'}
        else:
            raise Exception('Unknown node')

    for node in nodes:
        table = create_forwarding_table(cqx_topo, node)
        rp = RoutingProtocol(node, table)
        node.control_protocols.append(rp)

    # create quantum memories
    for i, node in enumerate(nodes):
        memory_params = {"fidelity": MEMO_FIDELITY, "efficiency": MEMO_EFFICIENCY}
        name = "memory_array_%s" % node.name
        memory_array = topology.MemoryArray(name, tl, num_memories=MEMO_ARR_SIZE,
                                            frequency=MEMO_ARR_FREQ,
                                            memory_params=memory_params)
        node.assign_memory_array(memory_array)

    # create RSVP protocol
    for node in nodes:
        rsvp = ResourceReservationProtocol(node)
        node.append_control_protocol(rsvp)

    # create classical channel
    DELAY = 10
    for i, node1 in enumerate(nodes):
        for j, node2 in enumerate(nodes):
            if i >= j:
                continue

            name = "cc_%s_%s" % (node1.name, node2.name)
            cc = topology.ClassicalChannel(name, tl, distance=10, delay=DELAY)
            cc.set_ends([node1, node2])

    # schedule events
    process = Process(node_wm.control_protocols[1], "request", ['UIUC', 0.9, 10, 1000, 5000])
    event = Event(0, process)
    tl.schedule(event)

    """
    process = Process(node_anl.control_protocols[1], "request", ['SL', 0.9, 90, 1500, 5000])
    event = Event(200, process)
    tl.schedule(event)

    process = Process(node_wm.control_protocols[1], "request", ['UIUC', 0.9, 10, 1500, 5000])
    event = Event(300, process)
    tl.schedule(event)
    """

    # start simulation
    tl.init()
    tl.run()

    # print states
