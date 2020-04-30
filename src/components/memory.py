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
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.memory_type = kwargs.get("memory_type", "atom")
        self.max_frequency = kwargs.get("frequency", 8e7)
        num_memories = kwargs.get("num_memories", 10)
        memory_params = kwargs.get("memory_params", {})
        self.memories = []
        self.frequency = self.max_frequency
        self.upper_protocols = []

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
        # self._pop(entity="MemoryArray", index=index)
        for protocol in self.upper_protocols:
            protocol.pop(info_type="expired_memory", index=index) 

    def set_direct_receiver(self, indices, direct_receiver):
        for memo_index in indices:
            self.memories[memo_index].direct_receiver = direct_receiver


# single-atom memory
class Memory(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 0)
        self.frequency = kwargs.get("frequency", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.coherence_time = kwargs.get("coherence_time", -1) # average coherence time in seconds
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.qstate = QuantumState()

        self.photon_encoding = single_atom.copy()
        self.photon_encoding["memory"] = self

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of current memory write (ignore expiration of past states)
        self.exicte_id = 0

        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

    def init(self):
        pass

    def excite(self, dst=""):
        state = self.qstate.measure(single_atom["bases"][0])
        # create photon and check if null
        photon = Photon("", wavelength=(1 / self.frequency), location=self,
                        encoding_type=self.photon_encoding)

        if state == 0:
            photon.is_null = True
        elif self.coherence_time > 0:
            self.excite_id += 1
            # set expiration
            decay_time = self.timeline.now() + int(numpy.random.exponential(self.coherence_time) * 1e12)
            process = Process(self, "expire", [self.excite_id])
            event = Event(decay_time, process)
            self.timeline.schedule(event)

        # send to direct receiver or node
        if (state == 0) or (numpy.random.random_sample() < self.efficiency):
            if self.direct_receiver:
                self.direct_receiver.get(photon)
            else:
                self.owner.send_qubit(dst, photon)

    def expire(self, excite_id):
        # check if valid expiration
        if self.excite_id == excite_id:
            self.fidelity = 0
            self.qstate.measure(single_atom["bases"][0]) # to unentangle
            self.entangled_memory = {'node_id': None, 'memo_id': None}
            # pop expiration message
            self._pop(memory=self)

    def flip_state(self):
        # flip coefficients of state
        # print(self.qstate.state)
        assert len(self.qstate.state) == 2, "qstate length error in memory {}".format(self.name)
        new_state = self.qstate.state
        new_state[0], new_state[1] = new_state[1], new_state[0]
        self.qstate.set_state_single(new_state)

    def reset(self):
        self.qstate.set_state_single([complex(1/math.sqrt(2)), complex(1/math.sqrt(2))])
        self.previous_bsm = -1
        self.entangled_memory = {'node_id': None, 'memo_id': None}


