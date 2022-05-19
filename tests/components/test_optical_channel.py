import numpy as np

from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node

SEED = 0


def test_ClassicalChannel_set_ends():
    tl = Timeline()
    cc = ClassicalChannel("cc", tl, 1e3)

    n1 = Node('n1', tl)
    n2 = Node('n2', tl)
    assert len(n1.cchannels) == 0 and len(n2.cchannels) == 0

    cc.set_ends(n1, n2.name)
    assert cc.sender == n1
    assert cc.receiver == n2.name
    assert 'n2' in n1.cchannels
    assert n1.cchannels["n2"] == cc
    assert len(n2.cchannels) == 0


def test_ClassicalChannel_transmit():
    class FakeNode(Node):
        def __init__(self, name, tl, **kwargs):
            Node.__init__(self, name, tl, **kwargs)
            self.msgs = []

        def receive_message(self, src: str, msg: str):
            self.msgs.append([tl.now(), src, msg])

    tl = Timeline()
    cc = ClassicalChannel("cc", tl, 1e3)

    n1 = FakeNode('n1', tl)
    n2 = FakeNode('n2', tl)
    cc.set_ends(n1, n2.name)

    args = [['1-1', n1, 5], ['1-2', n1, 5]]
    results = [[cc.delay, 'n1', '1-1'], [1 + cc.delay, 'n1', '1-2']]

    for arg in args:
        cc.transmit(arg[0], arg[1], arg[2])
        tl.time += 1

    tl.run()
    assert len(n1.msgs) == 0 and len(n2.msgs) == 2
    for msg, res in zip(n2.msgs, results):
        assert msg == res


def test_QuantumChannel_init():
    tl = Timeline()
    qc = QuantumChannel("qc", tl, attenuation=0.0002, distance=1e4)
    tl.init()
    assert qc.loss - 0.3690426555 > 1e-11 and qc.delay == 50000000


def test_QuantumChannel_set_ends():
    tl = Timeline()
    qc = QuantumChannel("qc", tl, attenuation=0.0002, distance=1e4)
    end1 = Node("end1", tl)
    end2 = Node("end2", tl)
    assert len(end1.qchannels) == len(end2.qchannels) == 0
    qc.set_ends(end1, end2.name)

    assert len(end1.qchannels) == 1
    assert len(end2.qchannels) == 0
    assert qc.sender == end1
    assert qc.receiver == end2.name
    assert end2.name in end1.qchannels


def test_QuantumChannel_transmit():
    from sequence.components.photon import Photon

    class FakeNode(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []
            self.generator = np.random.default_rng(SEED)

        def receive_qubit(self, src, photon):
            self.log.append((src, self.timeline.now(), photon.name))

        def get_generator(self):
            return self.generator

    tl = Timeline()
    qc = QuantumChannel("qc", tl, attenuation=0.0002, distance=1e4)
    sender = FakeNode("sender", tl)
    receiver = FakeNode("receiver", tl)
    sender.set_seed(0)
    receiver.set_seed(1)
    qc.set_ends(sender, receiver.name)
    tl.init()

    for i in range(1000):
        photon = Photon(str(i), tl)
        qc.transmit(photon, sender)
        tl.time = tl.time + 1

    assert len(sender.log) == len(receiver.log) == 0
    tl.run()

    expect_rate = 1 - qc.loss
    assert abs(len(receiver.log) / 1000 - expect_rate) < 0.1
    assert len(sender.log) == 0


def test_QuantumChannel_schedule_transmit():
    tl = Timeline()
    qc = QuantumChannel("qc", tl, attenuation=0, distance=1e3, frequency=1e12)

    # send at time 1 with low min time
    tl.time = 0
    time = qc.schedule_transmit(0)
    assert time == 0

    # high min time
    time = qc.schedule_transmit(2)
    assert time == 2

    # another with low
    time = qc.schedule_transmit(0)
    assert time == 1

    # new time 
    tl.time = 2
    time = qc.schedule_transmit(0)
    assert time == 3
