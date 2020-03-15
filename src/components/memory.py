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

        if self.memory_type == "atom":
            for i in range(num_memories):
                memory = AtomMemory(self.name + "[%d]" % i, timeline, **memory_params)
                memory.parents.append(self)
                self.memories.append(memory)

        elif self.memory_type == "ensemble":
            for i in range(num_memories):
                memory = Memory(self.name + "%d" % i, timeline, **memory_params)
                memory.parents.append(self)
                self.memories.append(memory)

        else:
            raise Exception("invalid memory type {}".format(self.memory_type))

    def __getitem__(self, key):
        return self.memories[key]

    def __len__(self):
        return len(self.memories)

    def init(self):
        pass

    def write(self):
        assert self.memory_type == "ensemble"

        time = self.timeline.now()

        period = 1e12 / min(self.frequency, self.max_frequency)

        for mem in self.memories:
            process = Process(mem, "write", [])
            event = Event(time, process)
            self.timeline.schedule(event)
            time += period

    def read(self):
        assert self.memory_type == "ensemble"

        time = self.timeline.now()

        period = 1e12 / min(self.frequency, self.max_frequency)

        for mem in self.memories:
            process = Process(mem, "read", [])
            event = Event(time, process)
            self.timeline.schedule(event)
            time += period

    def pop(self, **kwargs):
        memory = kwargs.get("memory")
        index = self.memories.index(memory)
        # notify node
        self._pop(entity="MemoryArray", index=index)

    def set_direct_receiver(self, indices, direct_receiver):
        for memo_index in indices:
            self.memories[memo_index].direct_receiver = direct_receiver


# single-atom memory
class AtomMemory(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 1)
        self.frequency = kwargs.get("frequency", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.coherence_time = kwargs.get("coherence_time", -1) # average coherence time in seconds
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.qstate = QuantumState()

        self.photon_encoding = single_atom.copy()
        self.photon_encoding["memory"] = self

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

    def init(self):
        pass

    def excite(self):
        state = self.qstate.measure(ensemble["bases"][0])
        # send photon in certain state to direct receiver
        photon = Photon("", wavelength=(1 / self.frequency), location=self,
                        encoding_type=self.photon_encoding)
        if state == 0:
            photon.is_null = True
            self.direct_receiver.get(photon)
        else:
            if numpy.random.random_sample() < self.efficiency:
                self.direct_receiver.get(photon)
            if self.coherence_time > 0:
                # set expiration
                decay_time = self.timeline.now() + int(numpy.random.exponential(self.coherence_time) * 1e12)
                process = Process(self, "expire", [])
                event = Event(decay_time, process)
                self.timeline.schedule(event)

    def expire(self):
        # TODO: change state?
        #   curently just send to upper protocols and handle changes there
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


# atomic ensemble memory for DLCZ/entanglement swapping
class Memory(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.coherence_time = kwargs.get("coherence_time", 1) # average coherence time in seconds
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.qstate = QuantumState()
        self.frequencies = kwargs.get("frequencies", [1, 1]) # first is ground transition frequency, second is excited frequency

        self.photon_encoding = ensemble.copy()
        self.photon_encoding["memory"] = self

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        self.expired = True

    def init(self):
        pass

    def write(self):
        self.qstate = QuantumState()
        self.entangled_memory = {'node_id': None, 'memo_id': None}
        if numpy.random.random_sample() < self.efficiency:
            # unentangle
            # set new state
            self.qstate.set_state([complex(0), complex(1)])
            # send photon in certain state to direct receiver
            photon = Photon("", wavelength=(1 / self.frequencies[1]), location=self,
                            encoding_type=self.photon_encoding)
            self.direct_receiver.get(photon)
        else:
            self.qstate.set_state([complex(0), complex(1)])
            photon = Photon("", location=self, encoding_type=self.photon_encoding)
            photon.is_null = True
            self.direct_receiver.get(photon)


        """
        self.expired = False
        # schedule decay based on coherence time
        decay_time = self.timeline.now() + int(numpy.random.exponential(self.coherence_time) * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)
        """

    def read(self):
        if numpy.random_random_sample() < self.efficiency:
            state = self.qstate.measure(ensemble["bases"][0])
            if state == 1:
                # send photon in certain state to direct receiver
                photon = Photon("", wavelength=(1 / self.frequencies[0]), location=self,
                                encoding_type=self.photon_encoding)
                self.direct_receiver.get(photon)

    def expire(self):
        if not self.expired:
            self.expired = True
            state = self.qstate.measure(ensemble["bases"][0])
            if state == 1:
                # send photon in certain state to direct receiver
                photon = Photon("", wavelength=(1 / self.frequencies[0]), location=self,
                                encoding_type=self.photon_encoding)
                self.direct_receiver.get(photon)

            self.entangled_partner.expire()

            # pop expired message to parent
            self._pop(memory=self)


# class for photon memory
class Memory_EIT(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.photon = None

    def init(self):
        pass

    def get(self, photon):
        photon.location = self
        self.photon = photon

    def retrieve_photon(self):
        photon = self.photon
        self.photon = None
        return photon
