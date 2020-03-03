import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class Photon(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.wavelength = kwargs.get("wavelength", 0)
        self.location = kwargs.get("location", None)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        quantum_state = kwargs.get("quantum_state", [complex(1), complex(0)])
        self.quantum_state = QuantumState()
        self.quantum_state.state = quantum_state
        self.entangled_photons = [self]
        self.is_null = False

    def init(self):
        pass

    def entangle(self, photon):
        self.quantum_state.entangle(photon.quantum_state)

    def random_noise(self):
        self.quantum_state.random_noise()

    def set_state(self, state):
        self.quantum_state.set_state(state)

    @staticmethod
    def measure(basis, photon):
        return photon.quantum_state.measure(basis)

    @staticmethod
    def measure_multiple(basis, photons):
        return QuantumState.measure_multiple(basis, [photon[0].quantum_state, photon[1].quantum_state])

    
