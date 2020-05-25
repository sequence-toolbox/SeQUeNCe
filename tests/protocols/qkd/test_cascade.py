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
    KEYSIZE = 64
    KEYNUM = 10

    tl = Timeline(1e10)

    alice = QKDNode("alice", tl)
    bob = QKDNode("bob", tl)
    pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])
    pair_cascade_protocols(alice.protocol_stack[1], bob.protocol_stack[1])

    qc = QuantumChannel("qc", tl, distance=1e3, attenuation=2e-5)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=1e3, attenuation=0)
    cc.set_ends(alice, bob)
    
    process = Process(alice.protocol_stack[1], "push", [KEYSIZE, KEYNUM])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()

    casc_a = alice.protocol_stack[1]
    casc_b = bob.protocol_stack[1]
    assert len(casc_a.valid_keys) == KEYNUM
    assert len(casc_a.valid_keys) == len(casc_b.valid_keys)
    assert casc_a.error_bit_rate == 0
    assert casc_a.valid_keys[0] < 2 ** 64  # check that key is not too large


