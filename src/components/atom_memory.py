import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


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

        self.photon_encoding = encoding.single_atom.copy()
        self.photon_encoding["memory"] = self

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

    def init(self):
        pass

    def excite(self):
        state = self.qstate.measure(encoding.ensemble["bases"][0])
        # send photon in certain state to direct receiver
        photon = Photon("", self.timeline, wavelength=(1/self.frequency), location=self,
                           encoding_type=self.photon_encoding)
        if state == 0:
            photon.is_null = True
            self.direct_receiver.get(photon)
        else:
            if numpy.random.random_sample() < self.efficiency:
                self.direct_receiver.get(photon)
            else:
                photon.remove_from_timeline()
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

