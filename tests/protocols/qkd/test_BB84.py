from numpy import random

from sequence.protocols.qkd.BB84 import pair_bb84_protocols

# For testing BB84 Protocol
from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.topology.node import QKDNode
from sequence.protocols.protocol import Protocol
from sequence.utils.encoding import *


random.seed(0)


# dummy parent class to test BB84 functionality
class Parent(Protocol):
    def __init__(self, own: "Node", keysize: int, role: str):
        Protocol.__init__(self, own, "")
        self.upper_protocols = []
        self.lower_protocols = []
        self.keysize = keysize
        self.role = role
        self.key = 0
        self.counter = 0

    def init(self):
        pass

    def pop(self, msg):
        self.key = msg
        self.counter += 1

    def push(self):
        self.lower_protocols[0].push(self.keysize, 10)

    def received_message(self):
        pass


def test_BB84_polarization(): 
    tl = Timeline(1e12)  # stop time is 1 s

    alice = QKDNode("alice", tl)
    bob = QKDNode("bob", tl)
    pair_bb84_protocols(alice.sifting_protocol, bob.sifting_protocol)

    qc = QuantumChannel("qc", tl, distance=10e3, polarization_fidelity=0.99, attenuation=0.00002)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=10e3, attenuation=0.00002)
    cc.set_ends(alice, bob)

    # Parent
    pa = Parent(alice, 128, "alice")
    pb = Parent(bob, 128, "bob")
    pa.lower_protocols.append(alice.sifting_protocol)
    pb.lower_protocols.append(bob.sifting_protocol)
    alice.sifting_protocol.upper_protocols.append(pa)
    bob.sifting_protocol.upper_protocols.append(pb)

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
    assert pa.counter == pb.counter == 10


def test_BB84_time_bin():
    tl = Timeline(1e12)  # stop time is 1 s

    alice = QKDNode("alice", tl, encoding=time_bin)
    bob = QKDNode("bob", tl, encoding=time_bin)
    pair_bb84_protocols(alice.sifting_protocol, bob.sifting_protocol)

    qc = QuantumChannel("qc", tl, distance=10e3, polarization_fidelity=0.99, attenuation=0.00002)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=10e3, attenuation=0.00002)
    cc.set_ends(alice, bob)

    # Parent
    pa = Parent(alice, 128, "alice")
    pb = Parent(bob, 128, "bob")
    pa.lower_protocols.append(alice.sifting_protocol)
    pb.lower_protocols.append(bob.sifting_protocol)
    alice.sifting_protocol.upper_protocols.append(pa)
    bob.sifting_protocol.upper_protocols.append(pb)

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
    assert pa.counter == pb.counter == 10


