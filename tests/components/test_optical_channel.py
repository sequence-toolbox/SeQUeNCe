import pytest
from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node


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
    n3 = Node('n3', tl)
    assert len(n1.cchannels) == 0 and len(n2.cchannels) == 0 and len(n3.cchannels) == 0

    cc.set_ends([n1, n2])
    assert 'n1' in n2.cchannels and 'n2' in n1.cchannels and len(n3.cchannels) == 0

    with pytest.raises(Exception):
        cc.set_ends([n1, n3])


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
    cc.set_ends([n1, n2])

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
