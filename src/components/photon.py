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
        encoding_type (Dict[str, Any]): encoding type of photon (as defined in encoding module).
        quantum_state (QuantumState): quantum state of photon.
        is_null (bool): defines whether photon is real or a "ghost" photon (not detectable but used in memory encoding).
    """

    def __init__(self, name, wavelength=0, location=None, encoding_type=polarization,
                 quantum_state=(complex(1), complex(0))):
        """Constructor for the photon class.

        Args:
            name (str): name of the photon instance.
            wavelength (int): wavelength of photon (in nm) (default 0).
            location (Entity): location of the photon (default None).
            encoding_type (Dict[str, Any]): encoding type of photon (from encoding module) (default polarization).
            quantum_state (List[complex]): complex coefficients for photon's quantum state (default [1, 0]).
        """

        self.name = name
        self.wavelength = wavelength
        self.location = location
        self.encoding_type = encoding_type
        if self.encoding_type["name"] == "single_atom":
            self.memory = None
        self.quantum_state = QuantumState()
        self.quantum_state.state = quantum_state
        self.qstate_key = None
        self.is_null = False

    def entangle(self, photon):
        """Method to entangle photons (see `QuantumState` module)."""

        self.quantum_state.entangle(photon.quantum_state)

    def random_noise(self):
        """Method to add random noise to photon's state (see `QuantumState` module)."""

        self.quantum_state.random_noise()

    def set_state(self, state):
        self.quantum_state.set_state(state)

    @staticmethod
    def measure(basis, photon):
        """Method to measure a photon (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photon.
            photon (Photon): photon to measure.

        Returns:
            int: 0/1 value giving result of measurement in given basis.
        """

        return photon.quantum_state.measure(basis)

    @staticmethod
    def measure_multiple(basis, photons):
        """Method to measure 2 entangled photons (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photons.
            photons (List[Photon]): list of 2 photons to measure.

        Returns:
            int: 0-3 value giving the result of measurement in given basis.
        """

        return QuantumState.measure_multiple(basis, [photons[0].quantum_state, photons[1].quantum_state])
