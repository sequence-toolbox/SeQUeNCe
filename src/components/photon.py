"""Model for single photon.

This module defines the Photon class for tracking individual photons.
Photons may be encoded directly with polarization or time bin schemes, or may herald the encoded state of single atom memories.
"""

from ..utils.encoding import polarization
from ..utils.quantum_state import QuantumState


class Photon():
    def __init__(self, name, wavelength=0, location=None, encoding_type=polarization,
                 quantum_state=[complex(1), complex(0)]):
        self.name = name
        self.wavelength = wavelength
        self.location = location
        self.encoding_type = encoding_type
        self.quantum_state = QuantumState()
        self.quantum_state.state = quantum_state
        # self.entangled_photons = [self]
        self.is_null = False

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
        return QuantumState.measure_multiple(basis, [photons[0].quantum_state, photons[1].quantum_state])
