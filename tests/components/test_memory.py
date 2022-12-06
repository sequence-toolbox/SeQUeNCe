import numpy as np
import math

from sequence.components.memory import *
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

SEED = 0


class DumbReceiver:
    def __init__(self):
        self.photon_list = []

    def get(self, photon, **kwargs):
        self.photon_list.append(photon)


class DumbParent:
    def __init__(self, memory):
        memory.attach(self)
        memory.add_receiver(self)
        memory.owner = self
        self.tl = memory.timeline
        self.pop_log = []
        self.photon_list = []
        self.photon_arrival_times = []
        self.generator = np.random.default_rng(SEED)

    def memory_expire(self, memory):
        self.pop_log.append(memory)

    def get(self, photon, **kwargs):
        self.photon_list.append(photon)
        self.photon_arrival_times.append(self.tl.now())

    def reset(self):
        self.photon_list = []
        self.photon_arrival_times = []

    def get_generator(self):
        return self.generator


class Owner:
    def __init__(self):
        self.generator = np.random.default_rng(SEED)

    def get_generator(self):
        return self.generator


def perfect_efficiency(_):
    return 1


def test_MemoryArray_init():
    tl = Timeline()
    ma = MemoryArray("ma", tl, num_memories=10)

    assert len(ma.memories) == 10
    for m in ma.memories:
        assert type(m) == Memory


def test_MemoryArray_expire():
    class FakeNode:
        def __init__(self, tl):
            self.timeline = tl
            self.ma = MemoryArray("ma", tl)
            self.ma.owner = self
            self.is_expired = False
            self.expired_memory = -1

        def memory_expire(self, memory: "Memory") -> None:
            self.is_expired = True
            self.expired_memory = memory

    tl = Timeline()
    node = FakeNode(tl)
    ma = node.ma
    expired_memo = ma[0]
    ma.memory_expire(expired_memo)
    assert node.is_expired is True and node.expired_memory == expired_memo


def test_Memory_update_state():
    new_state = [complex(0), complex(1)]
    
    tl = Timeline()
    mem = Memory("mem", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=-1, wavelength=500)

    mem.update_state(new_state)
    
    assert len(tl.quantum_manager.states) == 1
    assert np.all(tl.quantum_manager.get(mem.qstate_key).state == np.array(new_state))


def test_Memory_excite():
    NUM_TESTS = 1000

    tl = Timeline()
    rec = DumbReceiver()
    own = Owner()
    mem = Memory("mem", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=-1, wavelength=500)
    mem.add_receiver(rec)
    mem.owner = own

    # test with perfect efficiency

    for _ in range(NUM_TESTS):
        mem.excite()

    assert len(rec.photon_list) == NUM_TESTS
    for p in rec.photon_list:
        assert p.loss == 0

    # test with imperfect efficiency

    rec.photon_list = []
    mem.efficiency = 0.7
    mem.update_state([complex(0), complex(1)])

    for _ in range(NUM_TESTS):
        mem.excite()

    for p in rec.photon_list:
        assert p.loss == 1 - mem.efficiency


def test_Memory_expire():
    class FakeProtocol(EntanglementProtocol):
        def __init__(self, name):
            super().__init__(None, name)
            self.is_expire = False

        def set_others(self, other: "EntanglementProtocol") -> None:
            pass

        def start(self) -> None:
            pass

        def is_ready(self) -> bool:
            pass

        def memory_expire(self, memory) -> None:
            self.is_expire = True

        def received_message(self, src: str, msg: "Message"):
            pass

        def expire(self, memory: Memory):
            self.memory_expire(memory)

    tl = Timeline()
    mem = Memory("mem", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=-1, wavelength=500)
    parent = DumbParent(mem)
    protocol = FakeProtocol("upper_protocol")
    mem.attach(protocol)
    mem.update_state([math.sqrt(1/2), math.sqrt(1/2)])
    entangled_memory = {"node_id": "node", "memo_id": 0}
    mem.entangled_memory = entangled_memory

    # expire when the protocol controls memory
    mem.detach(parent)
    assert len(parent.pop_log) == 0 and protocol.is_expire is False
    mem.expire()
    assert np.all(tl.quantum_manager.get(mem.qstate_key).state == np.array([1, 0]))  # check if collapsed to |0> state
    assert mem.entangled_memory == {"node_id": None, "memo_id": None}
    assert len(parent.pop_log) == 0 and protocol.is_expire is True

    # expire when the resource manager controls memory
    mem.attach(parent)
    mem.detach(protocol)
    mem.update_state([math.sqrt(1/2), math.sqrt(1/2)])
    entangled_memory = {"node_id": "node", "memo_id": 0}
    mem.entangled_memory = entangled_memory
    mem.expire()
    assert len(parent.pop_log) == 1


def test_Memory__schedule_expiration():
    tl = Timeline()
    mem = Memory("mem", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=500)
    parent = DumbParent(mem)

    process = Process(mem, "expire", [])
    event = Event(1e12, process)
    tl.schedule(event)
    mem.expiration_event = event

    mem._schedule_expiration()

    counter = 0
    for event in tl.events:
        if event.is_invalid():
            counter += 1
    assert counter == 1


def test_Absorptive_prepare():
    PREPARE_TIME = 100
    tl = Timeline()
    mem = AbsorptiveMemory("mem", tl, 80e6, 1, perfect_efficiency, 100, 1550, PREPARE_TIME)
    # mem = AbsorptiveMemory("mem", tl, 80e6, 1, perfect_efficiency, 100, 0, 500, 0, PREPARE_TIME)

    tl.init()
    mem.prepare()
    assert len(tl.events) == 1
    event = tl.events.data[0]
    assert event.time == PREPARE_TIME
    process = event.process
    assert process.owner is mem
    assert process.activation == "_prepare_AFC"

    tl.run()
    assert mem.is_prepared


def test_Absorptive_get_all_bins():
    PERIOD = 1
    MODE_NUM = 100
    tl = Timeline()
    mem = AbsorptiveMemory("mem", tl, 1e12/PERIOD, 1, perfect_efficiency, MODE_NUM, 500)
    mem.is_prepared = True
    tl.init()

    # get first photon
    photon = Photon("", tl, 500)
    mem.get(photon)
    assert mem.absorb_start_time == 0
    stored = mem.stored_photons[0]
    assert stored is not None
    assert stored["photon"] is photon

    # get other photons
    for i in range(1, MODE_NUM):
        tl.time += PERIOD
        photon = Photon("", tl, 500)
        mem.get(photon)
        stored = mem.stored_photons[i]
        assert stored is not None
        assert stored["photon"] is photon

    assert mem.photon_counter == MODE_NUM


def test_Absorpive_get_skip_bins():
    PERIOD = 1
    tl = Timeline()
    mem = AbsorptiveMemory("mem", tl, 1e12/PERIOD, 1, perfect_efficiency, 100, 500)
    mem.is_prepared = True
    tl.init()

    # get first photon
    photon = Photon("", tl, 500)
    mem.get(photon)

    # get second after two periods
    tl.time += 2 * PERIOD
    photon = Photon("", tl, 500)
    mem.get(photon)
    assert mem.stored_photons[1] is None
    stored = mem.stored_photons[2]
    assert stored is not None
    assert stored["photon"] is photon


def test_Absorptive_retrieve():
    PERIOD = 1
    MODE_NUM = 100
    tl = Timeline()
    mem = AbsorptiveMemory("mem", tl, 1e12/PERIOD, 1, perfect_efficiency, MODE_NUM, 500)
    parent = DumbParent(mem)
    mem.is_prepared = True
    tl.init()

    mem.absorb_start_time = 0
    photons = [None] * MODE_NUM
    for i in range(MODE_NUM):
        photon = Photon(str(i), tl, 500)
        photons[i] = photon
        mem.stored_photons[i] = {"photon": photon, "time": i}
        mem.excited_photons.append(photon)

    # retrieve photons in forward order
    mem.retrieve()
    assert len(tl.events) == MODE_NUM
    tl.run()
    assert len(parent.photon_list) == MODE_NUM
    for i, time in enumerate(parent.photon_arrival_times):
        assert i == time
    for i, photon in enumerate(parent.photon_list):
        assert photons[i] == photon

    # retrieve photons in reverse order
    mem.is_prepared = True
    mem.is_spinwave = True
    mem.is_reversed = True
    parent.reset()
    tl.time = 0
    mem.absorb_start_time = 0
    photons = [None] * MODE_NUM
    for i in range(MODE_NUM):
        photon = Photon(str(i), tl, 500)
        photons[i] = photon
        mem.stored_photons[i] = {"photon": photon, "time": i}
        mem.excited_photons.append(photon)

    mem.retrieve()
    assert len(tl.events) == MODE_NUM
    tl.run()
    assert len(parent.photon_list) == MODE_NUM
    photon_list = parent.photon_list[:]
    photon_list.reverse()
    for i, time in enumerate(parent.photon_arrival_times):
        assert i == time
    for i, photon in enumerate(photon_list):
        assert photons[i] == photon


def test_Absorptive_expire():
    tl = Timeline()
    mem = AbsorptiveMemory("mem", tl, 80e6, 1, perfect_efficiency, 100, 500)
    parent = DumbParent(mem)

    process = Process(mem, "expire", [])
    event = Event(1e12, process)
    tl.schedule(event)
    mem.expiration_event = event

    mem._schedule_expiration()

    counter = 0
    for event in tl.events:
        if event.is_invalid():
            counter += 1
    assert counter == 1


def test_MemoryWithRandomCoherenceTime__schedule_expiration():
    NUM_TRIALS = 200
    coherence_period_avg = 1
    coherence_period_stdev = 0.15
    tl = Timeline()
    mem = MemoryWithRandomCoherenceTime("mem", tl, fidelity=1, frequency=0, efficiency=1, 
                 coherence_time=coherence_period_avg, coherence_time_stdev=coherence_period_stdev, 
                 wavelength=500)
    parent = DumbParent(mem)
    
    times_of_expiration_calculated = [0]
    np.random.seed(2)
    for i in range(NUM_TRIALS):
        times_of_expiration_calculated.append(times_of_expiration_calculated[-1]
                                              + int(mem.coherence_time_distribution()*1e12))
    times_of_expiration_calculated.pop(0)

    np.random.seed(2)
    process = Process(mem, "update_state", [[complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]])
    for i in range(NUM_TRIALS):
        event = Event(tl.now(), process)
        tl.schedule(event)        
        tl.init()
        tl.run()
        assert times_of_expiration_calculated[i] == tl.now()
        
    period_sum = times_of_expiration_calculated[0]
    period_squared_sum = times_of_expiration_calculated[0] ** 2
    for i in range(1, len(times_of_expiration_calculated)):
        period = times_of_expiration_calculated[i] - times_of_expiration_calculated[i-1]
        period_sum += period
        period_squared_sum += period*period
    
    avg_simulated = period_sum / NUM_TRIALS * 1e-12
    stdev_simulated = np.sqrt((period_squared_sum - period_sum * period_sum * 1.0/NUM_TRIALS) / NUM_TRIALS) * 1e-12

    #check that values in series are different
    assert stdev_simulated > 0.0
    #probability of error below is less then 0.3%
    assert abs(avg_simulated - coherence_period_avg) < 3 * coherence_period_stdev / np.sqrt(NUM_TRIALS)

