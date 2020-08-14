"""Model for single photon.

This module defines the Photon class for tracking individual photons.
Photons may be encoded directly with polarization or time bin schemes, or may herald the encoded state of single atom memories.
"""

from ..utils.encoding import polarization
from ..utils.quantum_state import QuantumState


class Photon():
    """Class for a single photon.

    Attributes:
        name (str): label for photon instance.
        wavelength (float): wavelength of photon (in nm).
        location (Entity): current location of photon.
        encoding_type (Dict): encoding type of photon (as defined in encoding module).
        quantum_state (QuantumState): quantum state of photon.
        is_null (bool): defines whether photon is real or a "ghost" photon (not detectable but used in memory encoding).
    """

    def __init__(self, name, **kwargs):
        self.name = name
        self.wavelength = kwargs.get("wavelength", 0)
        self.location = kwargs.get("location", None)
        self.encoding_type = kwargs.get("encoding_type", polarization)
        quantum_state = kwargs.get("quantum_state", [complex(1), complex(0)])
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
