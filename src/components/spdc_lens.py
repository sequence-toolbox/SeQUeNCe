"""Model for simulation of a SPDC Lens.

This module defines the SPDCLens class for creation of entangled photons.
"""

from copy import deepcopy

from numpy.random import random_sample

from ..kernel.entity import Entity


class SPDCLens(Entity):
    """Lens to create entangled photons (via SPDC).

    Attributes:
        name (str): label for SPDCLens instance. 
        timeline (Timeline): timeline for simulation.
        rate (float): probability of successful down conversion.
        direct_receiver (Entity): entity to receive entangled photons.
    """

    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.rate = kwargs.get("rate", 1)
        self.direct_receiver = kwargs.get("direct_receiver", None)

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
