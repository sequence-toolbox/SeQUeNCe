from numpy import random
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

random.seed(0)

from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.entanglement_management.purification import BBPSSW

class SimpleManager():
    def __init__(self):
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
        else:
            self.ent_counter += 1


class PurifyNode(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        self.kept_memo = Memory('%s.kept_memo' % name, tl, 0.9, 2000, 1, -1, 500)
        self.kept_memo.owner = self
        self.meas_memo = Memory('%s.meas_memo' % name, tl, 0.9, 2000, 1, -1, 500)
        self.meas_memo.owner = self
        self.resource_manager = SimpleManager()
        self.protocols = []

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)

    def create_protocol(self):
        self.protocols = [BBPSSW(self, 'purification_protocol', self.kept_memo, self.meas_memo)]


def entangle_memory(memo1: Memory, memo2: Memory, fidelity: float):
    memo1.reset()
    memo2.reset()

    memo1.entangled_memory['node_id'] = memo2.owner.name
    memo1.entangled_memory['memo_id'] = memo2.name
    memo2.entangled_memory['node_id'] = memo1.owner.name
    memo2.entangled_memory['memo_id'] = memo1.name

    memo1.fidelity = memo2.fidelity = fidelity


def pair_protocol(node1: Node, node2: Node):
    p1 = node1.protocols[0]
    p2 = node2.protocols[0]
    p1.set_others(p2.name, node2.name,
                  [node2.kept_memo.name, node2.meas_memo.name])
    p2.set_others(p1.name, node1.name,
                  [node1.kept_memo.name, node1.meas_memo.name])


tl = Timeline()

node1 = PurifyNode('node1', tl)
node2 = PurifyNode('node2', tl)
node1.set_seed(0)
node2.set_seed(1)

cc0 = ClassicalChannel('cc0', tl, 1000, 1e9)
cc1 = ClassicalChannel('cc1', tl, 1000, 1e9)
cc0.set_ends(node1, node2.name)
cc1.set_ends(node2, node1.name)

for i in range(10):
    entangle_memory(node1.kept_memo, node2.kept_memo, 0.9)
    entangle_memory(node1.meas_memo, node2.meas_memo, 0.9)

    node1.create_protocol()
    node2.create_protocol()

    pair_protocol(node1, node2)

    node1.protocols[0].start()
    node2.protocols[0].start()

    tl.init()
    tl.run()

    print(node1.kept_memo.name, node1.kept_memo.entangled_memory,
          node1.kept_memo.fidelity)
    print(node1.meas_memo.name, node1.meas_memo.entangled_memory,
          node1.meas_memo.fidelity)
