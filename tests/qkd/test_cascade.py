from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.protocol import StackProtocol
from sequence.qkd.BB84 import pair_bb84_protocols
from sequence.qkd.cascade import pair_cascade_protocols
from sequence.topology.node import QKDNode, Node


# dummy parent class to test cascade functionality
class Parent(StackProtocol):
    def __init__(self, own: "Node", keysize: int, keynum: int):
        super().__init__(own, "")
        self.upper_protocols = []
        self.lower_protocols = []
        self.keysize = keysize
        self.keynum = keynum
        self.keys = []
        self.counter = 0

    def init(self):
        pass

    def pop(self, key):
        self.keys.append(key)
        self.counter += 1

    def push(self):
        self.lower_protocols[0].push(self.keysize, self.keynum)

    def received_message(self):
        pass


def test_cascade_run():
    KEYSIZE = 512
    KEYNUM = 10

    tl = Timeline(1e11)

    alice = QKDNode("alice", tl)
    bob = QKDNode("bob", tl)
    alice.set_seed(0)
    bob.set_seed(0)
    pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])
    pair_cascade_protocols(alice.protocol_stack[1], bob.protocol_stack[1])

    qc0 = QuantumChannel("qc0", tl, distance=1e3, attenuation=2e-5,
                         polarization_fidelity=0.97)
    qc1 = QuantumChannel("qc1", tl, distance=1e3, attenuation=2e-5,
                         polarization_fidelity=0.97)
    qc0.set_ends(alice, bob.name)
    qc1.set_ends(bob, alice.name)
    cc0 = ClassicalChannel("cc0", tl, distance=1e3)
    cc1 = ClassicalChannel("cc1", tl, distance=1e3)
    cc0.set_ends(alice, bob.name)
    cc1.set_ends(bob, alice.name)

    # Parent
    pa = Parent(alice, KEYSIZE, KEYNUM)
    pb = Parent(bob, KEYSIZE, KEYNUM)
    alice.protocol_stack[1].upper_protocols.append(pa)
    pa.lower_protocols.append(alice.protocol_stack[1])
    bob.protocol_stack[1].upper_protocols.append(pb)
    pb.lower_protocols.append(bob.protocol_stack[1])

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()

    assert pa.counter == pb.counter == KEYNUM
    for k1, k2 in zip(pa.keys, pb.keys):
        assert k1 == k2
        assert k1 < 2 ** KEYSIZE  # check that key is not too large
    assert alice.protocol_stack[1].error_bit_rate == 0
