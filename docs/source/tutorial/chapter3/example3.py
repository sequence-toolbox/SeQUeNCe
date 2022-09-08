from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from sequence.message import Message


class SimpleManager:
    def __init__(self, own, memo_names):
        self.own = own
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
        if type(self.own) is SwapNodeA:
            left_memo = self.own.components[self.memo_names[0]]
            right_memo = self.own.components[self.memo_names[1]]
            self.own.protocols = [EntanglementSwappingA(self.own, 'ESA', left_memo, right_memo, 1, 0.99)]
        else:
            memo = self.own.components[self.memo_names[0]]
            self.own.protocols = [EntanglementSwappingB(self.own, '%s.ESB' % self.own.name, memo)]


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
        cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl,
                              1000, 1e9)
        cc.set_ends(nodes[i], nodes[j].name)

left_memo = left_node.components[left_node.resource_manager.memo_names[0]]
right_memo = right_node.components[right_node.resource_manager.memo_names[0]]
mid_left_memo = mid_node.components[mid_node.resource_manager.memo_names[0]]
mid_right_memo = mid_node.components[mid_node.resource_manager.memo_names[1]]
entangle_memory(left_memo, mid_left_memo, 0.9)
entangle_memory(right_memo, mid_right_memo, 0.9)

for node in nodes:
    node.resource_manager.create_protocol()

pair_protocol(left_node, right_node, mid_node)

tl.init()
for node in nodes:
    node.protocols[0].start()
tl.run()

print(left_memo.entangled_memory)
print(mid_left_memo.entangled_memory)
print(mid_right_memo.entangled_memory)
print(right_memo.entangled_memory)
print(left_memo.fidelity)
