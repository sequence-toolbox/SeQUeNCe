import pytest
from numpy import random
from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node

random.seed(1)


def test_ClassicalChannel_add_end():
    tl = Timeline()
    cc = ClassicalChannel("cc", tl, distance=1000, attenuation=2e-4, delay=1e9)
    assert cc.delay == 1e9

    n1 = Node('n1', tl)
    n2 = Node('n2', tl)
    n3 = Node('n3', tl)

    cc.add_end(n1)
    assert cc.ends[0] == n1

    with pytest.raises(Exception):
        cc.add_end(n1)

    cc.add_end(n2)
    assert cc.ends[0] == n1 and cc.ends[1] == n2 and len(cc.ends) == 2

    with pytest.raises(Exception):
        cc.add_end(n3)


def test_ClassicalChannel_set_ends():
    tl = Timeline()
    cc = ClassicalChannel("cc", tl, 2e-4, 1e3)

    n1 = Node('n1', tl)
    n2 = Node('n2', tl)
    assert len(n1.cchannels) == 0 and len(n2.cchannels) == 0

    cc.set_ends(n1, n2)
    assert 'n1' in n2.cchannels and 'n2' in n1.cchannels
    assert n1.cchannels["n2"] == n2.cchannels["n1"] == cc


def test_ClassicalChannel_transmit():
    class FakeNode(Node):
        def __init__(self, name, tl, **kwargs):
            Node.__init__(self, name, tl, **kwargs)
            self.msgs = []

        def receive_message(self, src: str, msg: str):
            self.msgs.append([tl.now(), src, msg])

    tl = Timeline()
    cc = ClassicalChannel("cc", tl, 2e-4, 1e3)

    n1 = FakeNode('n1', tl)
    n2 = FakeNode('n2', tl)
    cc.set_ends(n1, n2)

    args = [['1-1', n1, 5], ['1-2', n1, 5]]
    results = [[cc.delay, 'n1', '1-1'], [1 + cc.delay, 'n1', '1-2']]

    for arg in args:
        cc.transmit(arg[0], arg[1], arg[2])
        tl.time += 1

    tl.run()
    assert len(n1.msgs) == 0 and len(n2.msgs) == 2
    for msg, res in zip(n2.msgs, results):
        assert msg == res
    n2.msgs = []

    args = [['2-1', n2, 5], ['2-2', n2, 5]]
    results = [[2 + cc.delay, 'n2', '2-1'], [3 + cc.delay, 'n2', '2-2']]
    for arg in args:
        cc.transmit(arg[0], arg[1], arg[2])
        tl.time += 1

    tl.run()
    assert len(n1.msgs) == 2 and len(n2.msgs) == 0
    for msg, res in zip(n2.msgs, results):
        assert msg == res
    n1.msgs = []


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
    qc.set_ends(end1, end2)

    assert len(end1.qchannels) == len(end2.qchannels) == 1
    assert end1 in qc.ends and end2 in qc.ends
    assert end1.name in end2.qchannels and end2.name in end1.qchannels


def test_QuantumChannel_transmit():
    from sequence.components.photon import Photon
    random.seed(1)

    class FakeNode(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_qubit(self, src, photon):
            self.log.append((src, self.timeline.now(), photon.name))

    tl = Timeline()
    qc = QuantumChannel("qc", tl, attenuation=0.0002, distance=1e4)
    sender = FakeNode("sender", tl)
    receiver = FakeNode("receiver", tl)
    qc.set_ends(sender, receiver)
    tl.init()

    for i in range(10):
        photon = Photon(str(i))
        qc.transmit(photon, sender)
        tl.time = tl.time + 1

    for i in range(10):
        photon = Photon(str(i))
        qc.transmit(photon, receiver)
        tl.time = tl.time + 1

    assert len(sender.log) == len(receiver.log) == 0
    tl.run()
    res = [('sender', 50000000, '0'), ('sender', 50000001, '1'), ('sender', 50000008, '8'), ('sender', 50000009, '9')]
    for real, expect in zip(receiver.log, res):
        assert real == expect

    res = [('receiver', 50000010, '0'), ('receiver', 50000011, '1'), ('receiver', 50000013, '3'),
           ('receiver', 50000015, '5'), ('receiver', 50000016, '6'), ('receiver', 50000017, '7')]
    for real, expect in zip(sender.log, res):
        assert real == expect
