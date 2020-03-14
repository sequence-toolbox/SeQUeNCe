from ..control.routing import *
from ..control.rsvp import *
from ...components.memory import MemoryArray
from ...components.optical_channel import ClassicalChannel

if __name__ == "__main__":
    from sequence.topology.node import Node
    from sequence.kernel.timeline import Timeline


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

    tl = Timeline()
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
        memory_array = MemoryArray(name, tl, num_memories=MEMO_ARR_SIZE,
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
            cc = ClassicalChannel(name, tl, distance=10, delay=DELAY)
            cc.set_ends(node1, node2)

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
