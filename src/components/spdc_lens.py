import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class SPDCLens(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.rate = kwargs.get("rate", 1)
        self.direct_receiver = kwargs.get("direct_receiver", None)

    def init(self):
        pass

    def get(self, photon):
        if numpy.random.random_sample() < self.rate:
            state = photon.quantum_state
            photon.wavelength /= 2
            new_photon = copy.deepcopy(photon)

            photon.entangle(new_photon)
            photon.set_state([state[0], complex(0), complex(0), state[1]])

            self.direct_receiver.get(photon)
            self.direct_receiver.get(new_photon)

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver


