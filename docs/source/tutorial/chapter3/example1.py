from numpy import random
random.seed(0)

from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node, BSMNode
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol


class SimpleManager():
    def __init__(self):
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
        else:
            self.ent_counter += 1


class EntangleGenNode(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        self.memory = Memory('%s.memo'%name, tl, 0.9, 2000, 1, -1, 500)
        self.memory.owner = self
        self.resource_manager = SimpleManager()
        self.protocols = []

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)

    def create_protocol(self, middle: str, other: str):
        self.protocols = [EntanglementGenerationA(self, '%s.eg'%self.name, middle, other, self.memory)]


def pair_protocol(node1: Node, node2: Node):
    p1 = node1.protocols[0]
    p2 = node2.protocols[0]
    p1.set_others(p2.name, node2.name, [node2.memory.name])
    p2.set_others(p1.name, node1.name, [node1.memory.name])


tl = Timeline()

node1 = EntangleGenNode('node1', tl)
node2 = EntangleGenNode('node2', tl)
bsm_node = BSMNode('bsm_node', tl, ['node1', 'node2'])
node1.set_seed(0)
node2.set_seed(1)
bsm_node.set_seed(2)

bsm_node.bsm.update_detectors_params('efficiency', 1)

qc1 = QuantumChannel('qc1', tl, attenuation=0, distance=1000)
qc2 = QuantumChannel('qc2', tl, attenuation=0, distance=1000)
qc1.set_ends(node1, bsm_node.name)
qc2.set_ends(node2, bsm_node.name)

nodes = [node1, node2, bsm_node]

for i in range(3):
    for j in range(3):
        cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl,
                              1000, 1e8)
        cc.set_ends(nodes[i], nodes[j].name)

for i in range(1000):
    tl.time = tl.now() + 1e11
    node1.create_protocol('bsm_node', 'node2')
    node2.create_protocol('bsm_node', 'node1')
    pair_protocol(node1, node2)

    node1.memory.reset()
    node2.memory.reset()

    node1.protocols[0].start()
    node2.protocols[0].start()

    tl.init()
    tl.run()

print(node1.resource_manager.ent_counter, ':', node1.resource_manager.raw_counter)
