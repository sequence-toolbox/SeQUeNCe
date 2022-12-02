from sequence.qkd.BB84 import pair_bb84_protocols

# For testing BB84 Protocol
from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.topology.node import QKDNode, Node
from sequence.protocol import StackProtocol
from sequence.utils.encoding import *


# dummy parent class to test BB84 functionality
class Parent(StackProtocol):
    def __init__(self, own: "Node", keysize: int, role: str):
        super().__init__(own, "")
        self.upper_protocols = []
        self.lower_protocols = []
        self.keysize = keysize
        self.role = role
        self.key = 0
        self.counter = 0

    def init(self):
        pass

    def pop(self, info):
        self.key = info
        self.counter += 1

    def push(self):
        self.lower_protocols[0].push(self.keysize, 10)

    def received_message(self):
        pass


def test_BB84_polarization(): 
    tl = Timeline(1e12)  # stop time is 1 s

    alice = QKDNode("alice", tl, stack_size=1)
    bob = QKDNode("bob", tl, stack_size=1)
    alice.set_seed(0)
    bob.set_seed(1)
    pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])

    qc0 = QuantumChannel("qc0", tl, distance=10e3, polarization_fidelity=0.99,
                         attenuation=0.00002)
    qc1 = QuantumChannel("qc1", tl, distance=10e3, polarization_fidelity=0.99,
                         attenuation=0.00002)
    qc0.set_ends(alice, bob.name)
    qc1.set_ends(bob, alice.name)
    cc0 = ClassicalChannel("cc0", tl, distance=10e3)
    cc1 = ClassicalChannel("cc1", tl, distance=10e3)
    cc0.set_ends(alice, bob.name)
    cc1.set_ends(bob, alice.name)

    # Parent
    pa = Parent(alice, 128, "alice")
    pb = Parent(bob, 128, "bob")
    alice.protocol_stack[0].upper_protocols.append(pa)
    pa.lower_protocols.append(alice.protocol_stack[0])
    bob.protocol_stack[0].upper_protocols.append(pb)
    pb.lower_protocols.append(bob.protocol_stack[0])

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
    assert pa.counter == pb.counter == 10


def test_BB84_time_bin():
    tl = Timeline(1e12)  # stop time is 1 s

    alice = QKDNode("alice", tl, encoding=time_bin, stack_size=1)
    bob = QKDNode("bob", tl, encoding=time_bin, stack_size=1)
    alice.set_seed(2)
    bob.set_seed(3)
    pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])

    qc0 = QuantumChannel("qc0", tl, distance=10e3, polarization_fidelity=0.99,
                         attenuation=0.00002)
    qc1 = QuantumChannel("qc1", tl, distance=10e3, polarization_fidelity=0.99,
                         attenuation=0.00002)
    qc0.set_ends(alice, bob.name)
    qc1.set_ends(bob, alice.name)
    cc0 = ClassicalChannel("cc0", tl, distance=10e3)
    cc1 = ClassicalChannel("cc1", tl, distance=10e3)
    cc0.set_ends(alice, bob.name)
    cc1.set_ends(bob, alice.name)

    # Parent
    pa = Parent(alice, 128, "alice")
    pb = Parent(bob, 128, "bob")
    alice.protocol_stack[0].upper_protocols.append(pa)
    pa.lower_protocols.append(alice.protocol_stack[0])
    bob.protocol_stack[0].upper_protocols.append(pb)
    pb.lower_protocols.append(bob.protocol_stack[0])

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
    assert pa.counter == pb.counter == 10

