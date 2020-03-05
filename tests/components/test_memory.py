from sequence.kernel.timeline import Timeline


def test_MemoryArray_init():
    from sequence.components.memory import MemoryArray
    tl = Timeline()
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    assert len(ma.memories) == 10


def test_MemoryArray_write():
    assert False


def test_MemoryArray_read():
    assert False


def test_MemoryArray_pop():
    assert False


def test_MemoryArray_set_direct_receiver():
    assert False
