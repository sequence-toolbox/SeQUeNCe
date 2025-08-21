from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from sequence.message import Message


class SimpleManager:
    def __init__(self, owner, memo_names):
        self.owner = owner
        self.memo_names = memo_names
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
            memory.reset()
        else:
            self.ent_counter += 1

    def create_protocol(self):
        if type(self.owner) is SwapNodeA:
            left_memo = self.owner.components[self.memo_names[0]]
            right_memo = self.owner.components[self.memo_names[1]]
            self.owner.protocols = [EntanglementSwappingA(self.owner, 'ESA', left_memo, right_memo, 1, 0.99)]
        else:
            memo = self.owner.components[self.memo_names[0]]
            self.owner.protocols = [EntanglementSwappingB(self.owner, '%s.ESB' % self.owner.name, memo)]


class SwapNodeA(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        left_memo_name = '%s.left_memo' % name
        right_memo_name = '%s.right_memo' % name
        left_memo = Memory(left_memo_name, tl, 0.9, 2000, 1, -1, 500)
        right_memo = Memory(right_memo_name, tl, 0.9, 2000, 1, -1, 500)
        self.add_component(left_memo)
        self.add_component(right_memo)

        self.resource_manager = SimpleManager(self, [left_memo_name, right_memo_name])

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)


class SwapNodeB(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        memo_name = '%s.memo' % name
        memo = Memory(memo_name, tl, 0.9, 2000, 1, -1, 500)
        self.add_component(memo)

        self.resource_manager = SimpleManager(self, [memo_name])

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)

    def create_protocol(self):
        self.protocols = [EntanglementSwappingB(self, '%s.ESB'%self.name, self.memo)]


def entangle_memory(tl: Timeline, memo1: Memory, memo2: Memory, fidelity: float):
    SQRT_HALF = 0.5 ** 0.5
    phi_plus = [SQRT_HALF, 0, 0, SQRT_HALF]

    memo1.reset()
    memo2.reset()
    tl.quantum_manager.set([memo1.qstate_key, memo2.qstate_key], phi_plus)

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
                  [node_mid.resource_manager.memo_names[0], node_mid.resource_manager.memo_names[1]])
    p2.set_others(pmid.name, node_mid.name,
                  [node_mid.resource_manager.memo_names[0], node_mid.resource_manager.memo_names[1]])
    pmid.set_others(p1.name, node1.name, [node1.resource_manager.memo_names[0]])
    pmid.set_others(p2.name, node2.name, [node2.resource_manager.memo_names[0]])



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
        if i != j:
            cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl, 1000, 1e9)
            cc.set_ends(nodes[i], nodes[j].name)

left_memo = left_node.components[left_node.resource_manager.memo_names[0]]
right_memo = right_node.components[right_node.resource_manager.memo_names[0]]
mid_left_memo = mid_node.components[mid_node.resource_manager.memo_names[0]]
mid_right_memo = mid_node.components[mid_node.resource_manager.memo_names[1]]
entangle_memory(tl, left_memo, mid_left_memo, 0.9)
entangle_memory(tl, right_memo, mid_right_memo, 0.9)

for node in nodes:
    node.resource_manager.create_protocol()

pair_protocol(left_node, right_node, mid_node)

print('--------')
print('Before swapping:')
print(tl.quantum_manager.states[0], '\n')
print(tl.quantum_manager.states[1], '\n')
print(tl.quantum_manager.states[2], '\n')
print(tl.quantum_manager.states[3], '\n')

print(left_memo.entangled_memory)
print(mid_left_memo.entangled_memory)
print(mid_right_memo.entangled_memory)
print(right_memo.entangled_memory)
print(left_memo.fidelity)


tl.init()
for node in nodes:
    node.protocols[0].start()
tl.run()

print('--------')
print('after swapping:')
print(tl.quantum_manager.states[0], '\n')
print(tl.quantum_manager.states[1], '\n')
print(tl.quantum_manager.states[2], '\n')
print(tl.quantum_manager.states[3], '\n')

print(left_memo.entangled_memory)
print(mid_left_memo.entangled_memory)
print(mid_right_memo.entangled_memory)
print(right_memo.entangled_memory)
print(left_memo.fidelity)
