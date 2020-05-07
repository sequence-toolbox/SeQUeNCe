import math

import numpy

from .photon import Photon
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process
from ..utils.encoding import single_atom, ensemble
from ..utils.quantum_state import QuantumState


# array of atomic ensemble memories
class MemoryArray(Entity):
    def __init__(self, name, timeline, memory_type="atom", frequency=8e7, num_memories=10, memory_params={}):
        Entity.__init__(self, name, timeline)
        self.memory_type = memory_type
        self.max_frequency = frequency
        self.memories = []
        self.frequency = frequency

        if self.memory_type == "atom":
            for i in range(num_memories):
                memory = Memory(self.name + "[%d]" % i, timeline, **memory_params)
                memory.parents.append(self)
                self.memories.append(memory)
        else:
            raise Exception("invalid memory type {}".format(self.memory_type))

    def __getitem__(self, key):
        return self.memories[key]

    def __len__(self):
        return len(self.memories)

    def init(self):
        for mem in self.memories:
            mem.owner = self.owner

    def write(self):
        pass

    def read(self):
        pass

    def pop(self, **kwargs):
        memory = kwargs.get("memory")
        index = self.memories.index(memory)
        # notify protocol
        self._pop(info_type="expired_memory", index=index)


# single-atom memory
class Memory(Entity):
    def __init__(self, name, timeline, fidelity=0, frequency=80e6, efficiency=1, coherence_time=-1, wavelength=500):
        Entity.__init__(self, name, timeline)
        self.fidelity = fidelity
        self.frequency = frequency
        self.efficiency = efficiency
        self.coherence_time = coherence_time # average coherence time in seconds
        self.wavelength = wavelength
        self.qstate = QuantumState()

        self.photon_encoding = single_atom.copy()
        self.photon_encoding["memory"] = self
        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of current memory write (ignore expiration of past states)
        self.expiration_event = None

        self.next_excite_time = 0
        
    def init(self):
        pass

    def excite(self, dst=""):
        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time:
            return

        state = self.qstate.measure(single_atom["bases"][0])
        # create photon and check if null
        photon = Photon("", wavelength=self.wavelength, location=self,
                        encoding_type=self.photon_encoding)
        if state == 0:
            photon.is_null = True

        if self.frequency > 0:
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        # send to direct receiver or node
        if (state == 0) or (numpy.random.random_sample() < self.efficiency):
            self.owner.send_qubit(dst, photon)

    def expire(self):
        self.expiration_event = None
        self.reset()
        # pop expiration message
        self._pop(memory=self)

    def flip_state(self):
        # flip coefficients of state (apply x-gate)
        assert len(self.qstate.state) == 2, "qstate length error in memory {}".format(self.name)
        new_state = self.qstate.state
        new_state[0], new_state[1] = new_state[1], new_state[0]
        self.qstate.set_state_single(new_state)

    def reset(self):
        self.fidelity = 0
        if len(self.qstate.state) > 2:
            self.qstate.measure(single_atom["bases"][0]) # to unentangle
        self.qstate.set_state_single([complex(1), complex(0)]) # set to |0> state
        self.entangled_memory = {'node_id': None, 'memo_id': None}

    def set_plus(self):
        self.qstate.set_state_single([complex(1/math.sqrt(2)), complex(1/math.sqrt(2))])
        self.previous_bsm = -1
        self.entangled_memory = {'node_id': None, 'memo_id': None}
        
        # schedule expiration
        if self.coherence_time > 0:
            self._schedule_expiration()

    def _schedule_expiration(self):
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)

        decay_time = self.timeline.now() + int(numpy.random.exponential(self.coherence_time) * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)

        self.expiration_event = event


