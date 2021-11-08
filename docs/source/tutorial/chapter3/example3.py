from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB


class SimpleManager():
    def __init__(self):
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
            memory.entangled_memory['node_id'] = None
            memory.entangled_memory['memo_id'] = None
        else:
            self.ent_counter += 1


class SwapNodeA(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        self.left_memo = Memory('%s.left_memo' % name, tl, 0.9, 2000, 1, -1, 500)
        self.left_memo.owner = self
        self.right_memo = Memory('%s.right_memo' % name, tl, 0.9, 2000, 1, -1, 500)
        self.right_memo.owner = self
        self.resource_manager = SimpleManager()
        self.protocols = []

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)

    def create_protocol(self):
        self.protocols = [EntanglementSwappingA(self, 'ESA', self.left_memo, self.right_memo, 1, 0.99)]


class SwapNodeB(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        self.memo = Memory('%s.memo' % name, tl, 0.9, 2000, 1, -1, 500)
        self.memo.owner = self
        self.resource_manager = SimpleManager()
        self.protocols = []

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)

    def create_protocol(self):
        self.protocols = [EntanglementSwappingB(self, '%s.ESB'%self.name, self.memo)]


def entangle_memory(memo1: Memory, memo2: Memory, fidelity: float):
    memo1.reset()
    memo2.reset()

    memo1.entangled_memory['node_id'] = memo2.owner.name
    memo1.entangled_memory['memo_id'] = memo2.name
    memo2.entangled_memory['node_id'] = memo1.owner.name
    memo2.entangled_memory['memo_id'] = memo1.name

    memo1.fidelity = memo2.fidelity = fidelity


def pair_protocol(node1, node2, node_mid):
    p1 = node1.protocols[0]
    p2 = node2.protocols[0]
    pmid = node_mid.protocols[0]
    p1.set_others(pmid.name, node_mid.name,
                  [node_mid.left_memo.name, node_mid.right_memo.name])
    p2.set_others(pmid.name, node_mid.name,
                  [node_mid.left_memo.name, node_mid.right_memo.name])
    pmid.set_others(p1.name, node1.name, [node1.memo.name])
    pmid.set_others(p2.name, node2.name, [node2.memo.name])


tl = Timeline()

left_node = SwapNodeB('left', tl)
right_node = SwapNodeB('right', tl)
mid_node = SwapNodeA('mid', tl)
left_node.set_seed(0)
right_node.set_seed(1)
mid_node.set_seed(2)

nodes = [left_node, right_node, mid_node]

for i in range(3):
    for j in range(3):
        cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl,
                              1000, 1e9)
        cc.set_ends(nodes[i], nodes[j].name)

entangle_memory(left_node.memo, mid_node.left_memo, 0.9)
entangle_memory(right_node.memo, mid_node.right_memo, 0.9)

for node in nodes:
    node.create_protocol()

pair_protocol(left_node, right_node, mid_node)
for node in nodes:
    node.protocols[0].start()

tl.init()
tl.run()

print(left_node.memo.entangled_memory)
print(mid_node.left_memo.entangled_memory)
print(mid_node.right_memo.entangled_memory)
print(right_node.memo.entangled_memory)
print(left_node.memo.fidelity)
