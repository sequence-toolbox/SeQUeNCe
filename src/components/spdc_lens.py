"""Model for simulation of a SPDC Lens.

This module defines the SPDCLens class for creation of entangled photons.
"""

from copy import deepcopy

from numpy.random import random_sample

from ..kernel.entity import Entity


class SPDCLens(Entity):
    def __init__(self, name, timeline, rate=1, direct_receiver=None):
        Entity.__init__(self, name, timeline)
        self.rate = rate
        self.direct_receiver = direct_receiver

    def init(self):
        pass

    def get(self, photon):
        if random_sample() < self.rate:
            state = photon.quantum_state
            photon.wavelength /= 2
            new_photon = deepcopy(photon)

            photon.entangle(new_photon)
            photon.set_state([state[0], complex(0), complex(0), state[1]])

            self.direct_receiver.get(photon)
            self.direct_receiver.get(new_photon)

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver
