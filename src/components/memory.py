import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


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

        self.photon_encoding = encoding.ensemble.copy()
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
            photon = Photon("", self.timeline, wavelength=(1/self.frequencies[1]), location=self,
                            encoding_type=self.photon_encoding)
            self.direct_receiver.get(photon)
        else:
            self.qstate.set_state([complex(0), complex(1)])
            photon = Photon("", self.timeline, location=self, encoding_type=self.photon_encoding)
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
            state = self.qstate.measure(encoding.ensemble["bases"][0])
            if state == 1:
                # send photon in certain state to direct receiver
                photon = Photon("", self.timeline, wavelength=(1/self.frequencies[0]), location=self,
                                encoding_type=self.photon_encoding)
                self.direct_receiver.get(photon)

    def expire(self):
        if not self.expired:
            self.expired = True
            state = self.qstate.measure(encoding.ensemble["bases"][0])
            if state == 1:
                # send photon in certain state to direct receiver
                photon = Photon("", self.timeline, wavelength=(1/self.frequencies[0]), location=self,
                                encoding_type=self.photon_encoding)
                self.direct_receiver.get(photon)

            self.entangled_partner.expire()

            # pop expired message to parent
            self._pop(memory=self)

