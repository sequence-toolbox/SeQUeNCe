from numpy import random
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.protocols.protocol import StackProtocol
from sequence.protocols.qkd.BB84 import pair_bb84_protocols
from sequence.protocols.qkd.cascade import pair_cascade_protocols
from sequence.topology.node import QKDNode

random.seed(0)


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
    pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])
    pair_cascade_protocols(alice.protocol_stack[1], bob.protocol_stack[1])

    qc = QuantumChannel("qc", tl, distance=1e3, attenuation=2e-5, polarization_fidelity=0.97)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=1e3)
    cc.set_ends(alice, bob)

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
