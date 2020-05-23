from numpy import random

from sequence.protocols.qkd.cascade import *

# for testing protocol
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import *
from sequence.topology.node import QKDNode
from sequence.protocols.protocol import Protocol
from sequence.protocols.qkd.BB84 import pair_bb84_protocols


random.seed(0)


def test_cascade_run():
    tl = Timeline(1e9)

    alice = QKDNode("alice", tl)
    bob = QKDNode("bob", tl)
    pair_bb84_protocols(alice.sifting_protocol, bob.sifting_protocol)

    qc = QuantumChannel("qc", tl, distance=10e3, attenuation=2e-5)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=10e3, attenuation=0)
    cc.set_ends(alice, bob)

    # cascade
    casc_a = Cascade(alice, "cascade_alice")
    alice.protocols.append(casc_a)
    casc_b = Cascade(bob, "cascade_bob")
    bob.protocols.append(casc_b)
    pair_cascade_protocols(casc_a, casc_b)  # also adds protocols to stack
    
    process = Process(casc_a, "push", [128])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()


