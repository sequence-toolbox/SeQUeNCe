from sequence.kernel.timeline import Timeline
from sequence.components.memory import *


class DumbReceiver():
        def __init__(self):
            self.photon_list = []

        def get(self, photon):
            self.photon_list.append(photon)


def test_MemoryArray_init():
    tl = Timeline()
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})

    assert len(ma.memories) == 10
    for m in ma.memories:
        assert type(m) == AtomMemory


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


def test_AtomMemory_excite():
    NUM_TESTS = 1000

    tl = Timeline()
    rec = DumbReceiver()
    mem = AtomMemory("mem", tl, direct_receiver=rec)

    # test with perfect efficiency

    mem.qstate.set_state_single([complex(1), complex(0)])

    for _ in range(NUM_TESTS):
        mem.excite()

    assert len(rec.photon_list) == NUM_TESTS
    null_photons = [p for p in rec.photon_list if p.is_null]
    null_ratio = len(null_photons) / NUM_TESTS
    assert null_ratio == 1

    # test with imperfect efficiency
    
    rec.photon_list = []
    mem.efficiency = 0.7
    mem.qstate.set_state_single([complex(0), complex(1)])

    for _ in range(NUM_TESTS):
        mem.excite()

    assert abs(len(rec.photon_list) / NUM_TESTS - 0.7) < 0.1
    null_photons = [p for p in rec.photon_list if p.is_null]
    null_ratio = len(null_photons) / len(rec.photon_list)
    assert null_ratio == 0

    # test with perfect efficiency, + state

    rec.photon_list = []
    mem.efficiency = 1

    for _ in range(NUM_TESTS):
       mem.reset()
       mem.excite()

    assert len(rec.photon_list) == NUM_TESTS
    null_photons = [p for p in rec.photon_list if p.is_null]
    null_ratio = len(null_photons) / NUM_TESTS
    assert abs(null_ratio - 0.5) < 0.1


def test_AtomMemory_flip_state():
    tl = Timeline()
    rec = DumbReceiver()
    mem = AtomMemory("mem", tl, direct_receiver=rec)
    mem.qstate.set_state_single([complex(1), complex(0)])

    mem.excite()
    mem.flip_state()
    mem.excite()

    assert rec.photon_list[0].is_null
    assert not rec.photon_list[1].is_null


