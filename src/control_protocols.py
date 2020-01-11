from abc import ABC

from protocols import Protocol

from sequence import topology
from sequence.process import Process
from sequence.event import Event

class Message(ABC):
    def __init__(self, msg_type):
        self.msg_type = msg_type
        self.owner_type = None
        self.payload = None

class RoutingProtocol(Protocol):
    def __init__(self, own, forwarding_table):
        '''
        forwarding_table: {name of destination node: name of next node}
        '''
        if own is None: return
        Protocol.__init__(self, own)
        self.forwarding_table = forwarding_table

    def push(self, msg, dst):
        assert dst in self.forwarding_table

        next_node = self.forwarding_table[dst]
        msg = RoutingMessage(None, payload=msg)
        self.own.send_message(next_node, msg)

    def pop(self):
        pass

    def received_message(self, src, msg):
        print(self.own.timeline.now(), ':', self.own.name, "received_message from", src, "; msg is (", msg, ")")
        self._pop(msg=msg.payload, src=src)

    def init(self):
        pass


class RoutingMessage(Message):
    def __init__(self, msg_type, payload):
        Message.__init__(self, msg_type)
        self.owner_type = type(RoutingProtocol(None, None))
        self.payload = payload


class ResourceReservationProtocol(Protocol):
    def __init__(self, own):
        if own is None: return
        Protocol.__init__(self, own)
        self.reservation = []
        self.qcap = None

    def request(self, responder, fidelity, memory_size, start_time, end_time):
        msg = ResourceReservationMessage(msg_type="REQUEST")
        msg.initiator = self.own.name
        msg.responder = responder
        msg.fidelity = fidelity
        msg.memory_size = memory_size
        msg.start_time = start_time
        msg.end_time = end_time
        print(self.own.timeline.now(), self.own.name, "RSVP request", msg)
        self._push(msg=msg, dst=responder)

    def push(self):
        pass

    def pop(self, msg, src):
        print("   RSVP pop is called, src: ", src, "msg:", msg)
        if self.own.name != msg.responder:
            self._push(msg=msg, dst=msg.responder)
        else:
            print("   msg arrives dst", self.own.name, "; msg is ", msg)

    def received_message(self, src, msg):
        raise Exceptioin("RSVP protocol should not call this function")

    def init(self):
        memory_array = self.own.components['MemoryArray']
        for memory in memory_array:
            self.reservation.append([])

class ResourceReservationMessage(Message):
    def __init__(self, msg_type):
        Message.__init__(self, msg_type)
        self.owner_type = type(ResourceReservationProtocol(None))
        self.responder = None
        self.initiator = None
        if self.msg_type == "REQUEST":
            self.fidelity = None
            self.memory_size = None
            self.start_time = None
            self.end_time = None
            self.qcaps = []

    def __str__(self):
        if self.msg_type == "REQUEST":
            return "ResourceReservationMessage: \n\ttype=%s, \n\tresponder=%s, \n\tfidelity=%.2f, \n\tmemory_size=%d, \n\tstart_time=%d, \n\tend_time=%d, \n\tqcaps=%s" % (self.msg_type, self.responder, self.fidelity, self.memory_size, self.start_time, self.end_time, self.qcaps)


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

    tl = timeline.Timeline()
    MEMO_ARR_SIZE = 100
    cqx_topo = {'WM': {'SL': 241, 'FNL': 202},
                'SL': {'WM': 241, 'FNL': 66, 'ANL': 42, 'UIUC': 222, 'UC': 15, 'NU': 20},
                'NU': {'SL': 20, 'UC': 33},
                'UC': {'SL': 15, 'NU': 33},
                'FNL': {'WM': 202, 'SL': 66, 'ANL': 48},
                'ANL': {'FNL': 48, 'UIUC': 206, 'SL': 42},
                'UIUC': {'ANL': 206, 'SL': 222} }

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
    process = Process(node_wm.control_protocols[1], "request", ['UIUC', 0.9, 100, 1000, 5000])
    event = Event(0, process)
    tl.schedule(event)

    # start simulation
    tl.init()
    tl.run()

