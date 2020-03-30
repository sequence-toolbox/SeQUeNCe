from sequence.kernel.timeline import Timeline
from sequence.components.memory import *


def test_MemoryArray_init():
    tl = Timeline()
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})

    assert len(ma.memories) == 10
    for m in ma.memories:
        assert type(m) == AtomMemory

def test_MemoryArray_write():
    assert True


def test_MemoryArray_read():
    assert True


def test_MemoryArray_pop():
    class DumbProtocol():
        def __init__(self):
            self.pop_list = []

        def pop(self, **kwargs):
            self.pop_list.append(kwargs)

    tl = Timeline()
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    protocol = DumbProtocol()
    ma.upper_protocols.append(protocol)
    ma.pop(memory=ma[0])

    assert len(protocol.pop_list) == 1
    kwargs = protocol.pop_list[0]
    assert kwargs["info_type"] == "expired_memory"
    assert kwargs["index"] == 0

def test_MemoryArray_set_direct_receiver():
    assert True
