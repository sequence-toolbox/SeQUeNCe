from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.entanglement_management.purification import BBPSSW
from sequence.message import Message


class SimpleManager:
    def __init__(self, owner, kept_memo_name, meas_memo_name):
        self.owner = owner
        self.kept_memo_name = kept_memo_name
        self.meas_memo_name = meas_memo_name
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
            memory.reset()
        else:
            self.ent_counter += 1

    def create_protocol(self):
        kept_memo = self.owner.components[self.kept_memo_name]
        meas_memo = self.owner.components[self.meas_memo_name]
        self.owner.protocols = [BBPSSW(self.owner, 'purification_protocol', kept_memo, meas_memo)]


class PurifyNode(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        kept_memo_name = '%s.kept_memo' % name
        meas_memo_name = '%s.meas_memo' % name
        kept_memo = Memory('%s.kept_memo' % name, tl, 0.9, 2000, 1, -1, 500)
        meas_memo = Memory('%s.meas_memo' % name, tl, 0.9, 2000, 1, -1, 500)
        self.add_component(kept_memo)
        self.add_component(meas_memo)

        self.resource_manager = SimpleManager(self, kept_memo_name, meas_memo_name)

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)


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


def pair_protocol(node1: Node, node2: Node):
    p1 = node1.protocols[0]
    p2 = node2.protocols[0]
    kept_memo_1_name = node1.resource_manager.kept_memo_name
    meas_memo_1_name = node1.resource_manager.meas_memo_name
    kept_memo_2_name = node2.resource_manager.kept_memo_name
    meas_memo_2_name = node2.resource_manager.meas_memo_name
    p1.set_others(p2.name, node2.name, [kept_memo_2_name, meas_memo_2_name])
    p2.set_others(p1.name, node1.name, [kept_memo_1_name, meas_memo_1_name])


tl = Timeline()

node1 = PurifyNode('node1', tl)
node2 = PurifyNode('node2', tl)
node1.set_seed(0)
node2.set_seed(1)

cc0 = ClassicalChannel('cc0', tl, 1000, 1e9)
cc1 = ClassicalChannel('cc1', tl, 1000, 1e9)
cc0.set_ends(node1, node2.name)
cc1.set_ends(node2, node1.name)

kept_memo_1 = node1.components[node1.resource_manager.kept_memo_name]
kept_memo_2 = node2.components[node2.resource_manager.kept_memo_name]
meas_memo_1 = node1.components[node1.resource_manager.meas_memo_name]
meas_memo_2 = node2.components[node2.resource_manager.meas_memo_name]

tl.init()
for i in range(10):
    entangle_memory(tl, kept_memo_1, kept_memo_2, 0.9)  # this version of purification always success, need to fix
    entangle_memory(tl, meas_memo_1, meas_memo_2, 0.9)

    node1.resource_manager.create_protocol()
    node2.resource_manager.create_protocol()

    pair_protocol(node1, node2)

    node1.protocols[0].start()
    node2.protocols[0].start()
    tl.run()

    print(kept_memo_1.name, kept_memo_1.entangled_memory, kept_memo_1.fidelity)
    print(meas_memo_1.name, meas_memo_1.entangled_memory, meas_memo_1.fidelity)
