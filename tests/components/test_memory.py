import math
from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.memory import *


class DumbReceiver():
    def __init__(self):
        self.photon_list = []

    def send_qubit(self, dst, photon):
        self.photon_list.append(photon)

class DumbParent():
    def __init__(self, memory):
        memory.parents.append(self)
        self.pop_log = []

    def pop(self, **kwargs):
        self.pop_log.append(kwargs["memory"])


def test_MemoryArray_init():
    tl = Timeline()
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})

    assert len(ma.memories) == 10
    for m in ma.memories:
        assert type(m) == Memory


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


def test_Memory_excite():
    NUM_TESTS = 1000

    tl = Timeline()
    rec = DumbReceiver()
    mem = Memory("mem", tl, frequency=0)
    mem.owner = rec

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
       mem.set_plus()
       mem.excite()

    assert len(rec.photon_list) == NUM_TESTS
    null_photons = [p for p in rec.photon_list if p.is_null]
    null_ratio = len(null_photons) / NUM_TESTS
    assert abs(null_ratio - 0.5) < 0.1


def test_Memory_flip_state():
    tl = Timeline()
    rec = DumbReceiver()
    mem = Memory("mem", tl, frequency=0)
    mem.owner = rec
    mem.qstate.set_state_single([complex(1), complex(0)])

    mem.excite()
    mem.flip_state()
    mem.excite()

    assert rec.photon_list[0].is_null
    assert not rec.photon_list[1].is_null


def test_Memory_expire():
    tl = Timeline()
    mem = Memory("mem", tl)
    parent = DumbParent(mem)
    mem.set_plus()
    entangled_memory = {"node_id": "node", "memo_id": 0}
    mem.entangled_memory = entangled_memory

    mem.expire()
    assert [complex(1), complex(0)] == mem.qstate.state # check if collapsed to |0> state
    assert mem.entangled_memory == {"node_id": None, "memo_id": None}


def test_Memory__schedule_expiration():
    tl = Timeline()
    mem = Memory("mem", tl, coherence_time=1)
    parent = DumbParent(mem)
    
    process = Process(mem, "expire", [])
    event = Event(1e12, process)
    tl.schedule(event)
    mem.expiration_event = event

    mem._schedule_expiration()

    assert len(tl.events) == 1


