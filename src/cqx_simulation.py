from numpy import random

from sequence import topology
from sequence import timeline
from sequence import encoding
from sequence.topology import Node
from sequence.process import Process
from sequence.event import Event

from protocols import EntanglementGeneration, BBPSSW, EntanglementSwapping, Protocol

from control_protocols import Message, RoutingProtocol, ResourceReservationProtocol

# Memory parameters
MEMO_ARR_SIZE = 100
MEMO_FIDELITY = 0.8
MEMO_EFFICIENCY = 0.5
MEMO_ARR_FREQ = int(1e6)
MEMO_LIFE_TIME = 1e12

# Detector parameters
DETECTOR_DARK = 0
DETECTOR_EFFICIENCY = 0.9
DETECTOR_TIME_RESOLUTION = 150
DETECTOR_COUNT_RATE = 25000000

REPEATER_GAP = 40000
HOP_DELAY = 5e9

SEED_NUM = 0

random.seed(SEED_NUM)

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


class MiddleNode(Node):
    def __init__(self, name, timeline, **kwargs):
        Node.__init__(self, name, timeline, **kwargs)
        detectors = [{"efficiency":DETECTOR_EFFICIENCY,
                      "dark_count":DETECTOR_DARK,
                      "time_resolution":DETECTOR_TIME_RESOLUTION,
                      "count_rate":DETECTOR_COUNT_RATE}] * 2
        bsm = topology.BSM("bsm_%s" % name, timeline, encoding_type=encoding.ensemble, detectors=detectors)
        self.assign_bsm(bsm)
        # print('add', bsm.name, 'to', self.name)

    def create_protocol(self, neighbor1: str, neighbor2: str):
        eg = EntanglementGeneration(self, others=[neighbor1, neighbor2])


class Application(Protocol):
    def __init__(self, own):
        Protocol.__init__(self, own)
        self.others = ['WM', 'SL', 'NU', 'UC', 'FNL', 'ANL', 'UIUC']
        self.others.remove(own.name)
        self.total = 0
        self.success_counter = 0

    def start(self, pre_stop_time=0):
        assert len(self.lower_protocols) > 0 and isinstance(self.lower_protocols[0], ResourceReservationProtocol)
        self.total += 1
        rand_num = random.randint(0, len(self.others))
        responder = self.others[rand_num]
        fidelity = random.uniform(0.7, 0.9)
        memory_size = random.randint(10, MEMO_ARR_SIZE // 2)
        request_time = pre_stop_time + random.randint(1, 10) * 1e11
        start_time = request_time + random.randint(2, 10) * 1e12
        end_time = start_time + random.randint(10, 20) * 1e12
        process = Process(self.lower_protocols[0], "request", [responder, fidelity, memory_size, start_time, end_time])
        event = Event(request_time, process)
        self.own.timeline.schedule(event)

    def init(self):
        pass

    def push(self):
        pass

    def pop(self, msg):
        if msg.msg_type == "REQUEST":
            self.start(msg.end_time)
        elif msg.msg_type == "REJECT":
            self.start(self.own.timeline.now())
        elif msg.msg_type == "RESPONSE":
            self.success_counter += 1

    def received_message(self, msg):
        pass


def create_nodes(topo, tl):
    # create quantum routers
    routers = {}
    for name in topo.keys():
        node = QuantumRouter(name, tl)
        routers[name] = node

    # create quantum repeaters
    repeater_links = {}
    for name1 in topo:
        for name2 in topo[name1]:
            if name2 + '-' + name1 in repeater_links:
                continue
            link_name = name1 + '-' + name2
            repeater_links[link_name] = []
            for _ in range(REPEATER_GAP, topo[name1][name2], REPEATER_GAP):
                node_name = "repeater_" + link_name + str(len(repeater_links[link_name]))
                node = QuantumRouter(node_name, tl)
                repeater_links[link_name].append(node)

    return routers, repeater_links

cqx_topo = {'WM': {'SL': 241000, 'FNL': 202000},
            'SL': {'WM': 241000, 'FNL': 66000, 'ANL': 42000, 'UIUC': 222000, 'UC': 15000, 'NU': 20000},
            'NU': {'SL': 20000, 'UC': 33000},
            'UC': {'SL': 15000, 'NU': 33000},
            'FNL': {'WM': 202000, 'SL': 66000, 'ANL': 48000},
            'ANL': {'FNL': 48000, 'UIUC': 206000, 'SL': 42000},
            'UIUC': {'ANL': 206000, 'SL': 222000} }


# next router by shortest path algorithm
def next_router(node):
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

# create timeline
tl = timeline.Timeline(200e12)

# create nodes
routers, repeater_links = create_nodes(cqx_topo, tl)
nodes = []
nodes += list(routers.values())
for v in repeater_links.values():
    nodes += v

# create quantum memories
for node in nodes:
    memory_params = {"fidelity":MEMO_FIDELITY, "efficiency":MEMO_EFFICIENCY}
    name = "memory_array_%s" % node.name
    memory_array = topology.MemoryArray(name, tl, num_memories=MEMO_ARR_SIZE,
                                        frequency=MEMO_ARR_FREQ,
                                        memory_params=memory_params)
    node.assign_memory_array(memory_array)
    # print('add', name, 'to', node.name)

middle_nodes = []
# create channels
for link_name in repeater_links:
    name1, name2 = link_name.split("-")
    end1, end2 = routers[name1], routers[name2]
    link = [end1] + repeater_links[link_name] + [end2]

    # create classical channels
    # print(name1, '...', name2)
    # print("---- create classical channels ----")
    for i, node in enumerate(link):
        if i > 0:
            cc_name = "CC_(%s)_(%s)" % (link[i-1].name, node.name)
            cc = topology.ClassicalChannel(cc_name, tl, distance=REPEATER_GAP, delay=HOP_DELAY)
            cc.set_ends([link[i-1], node])
            # print('   ', cc_name, ':', node.name, '<->', link[i-1].name)

    # create middle nodes and quantum channels
    # print("---- create middle nodes and quantum channels ----")
    total_len = cqx_topo[name1][name2]
    for i, node in enumerate(link):
        if i > 0:
            # previous node <-> middle node <-> last node
            mid_node = MiddleNode('M_%s_%s' % (link[i-1].name, node.name), tl)
            # print("    create middle node", mid_node.name)
            distance = min(i * REPEATER_GAP, total_len) - (i - 1) * REPEATER_GAP

            # create quantum channel betwee middle node and previous node
            qc_name = "QC_(%s)_(%s)" % (mid_node.name, node.name)
            qc = topology.QuantumChannel(qc_name, tl, distance=distance/2)
            qc.set_sender(node.components['MemoryArray'])
            qc.set_receiver(mid_node.components["BSM"])
            node.assign_qchannel(qc)
            mid_node.assign_qchannel(qc)
            # print("    create qc", qc_name, "distance",  distance / 2)

            # create quantum channel betwee middle node and last node
            qc_name = "QC_(%s)_(%s)" % (mid_node.name, link[i-1].name)
            qc = topology.QuantumChannel(qc_name, tl, distance=distance/2)
            qc.set_sender(link[i-1].components['MemoryArray'])
            qc.set_receiver(mid_node.components["BSM"])
            link[i-1].assign_qchannel(qc)
            mid_node.assign_qchannel(qc)
            # print("    create qc", qc_name, "distance", distance / 2)

            # create protocol stack of middle node
            mid_node.create_protocol(node.name, link[i-1].name)

# create routing table for routing protocol
for node in nodes:
    rp = RoutingProtocol(node, {})
    node.append_control_protocol(rp)

for r1_name in routers:
    ft = next_router(routers[r1_name])
    for dst in ft:
        # print(r1_name, '->', dst)
        r2_name = ft[dst]
        if r1_name + '-' + r2_name in repeater_links:
            link_name = r1_name + '-' + r2_name
            link = [routers[r1_name]] + repeater_links[link_name] + [routers[r2_name]]
            for i, node in enumerate(link):
                if i < len(link) - 1 and dst != node.name:
                    node.control_protocols[0].add_forwarding_rule(dst, link[i+1].name)
        elif r2_name + '-' + r1_name in repeater_links:
            link_name = r2_name + '-' + r1_name
            link = [routers[r1_name]] + repeater_links[link_name][::-1] + [routers[r2_name]]
            for i, node in enumerate(link):
                if i < len(link) - 1 and dst != node.name:
                    node.control_protocols[0].add_forwarding_rule(dst, link[i+1].name)
        else:
            raise Exception("Unkown path, r1_name:", r1_name, "r2_name:", r2_name)

# create RSVP protocol
for node in nodes:
    rsvp = ResourceReservationProtocol(node)
    node.append_control_protocol(rsvp)

# create app
apps = []
for node in routers.values():
    app = Application(node)
    node.append_control_protocol(app)
    apps.append(app)

# schedule events
'''
process = Process(routers["WM"].control_protocols[1], "request", ['UIUC', 0.9, 10, 1e12, 2e12])
event = Event(0, process)
tl.schedule(event)
'''
for router in routers.values():
    process = Process(router.control_protocols[2], "start", [])
    event = Event(0, process)
    tl.schedule(event)

# start simulation
tl.init()
tl.run()

# print state
total = 0
success = 0
for app in apps:
    total += app.total
    success += app.success_counter
    print(app.total, app.success_counter)

print(total, success, success / total)
