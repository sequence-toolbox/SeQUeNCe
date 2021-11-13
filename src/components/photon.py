"""Model for single photon.

This module defines the Photon class for tracking individual photons.
Photons may be encoded directly with polarization or time bin schemes, or may herald the encoded state of single atom memories.
"""
from numpy.random._generator import Generator
from typing import Dict, Any, Optional

from ..kernel.entity import Entity
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

        self.name: str = name
        self.wavelength: int = wavelength
        self.location: Entity = location
        self.encoding_type: Dict[str, Any] = encoding_type
        if self.encoding_type["name"] == "single_atom":
            self.memory = None
            self.fidelity: Optional[float] = None
            self.detector_num: Optional[int] = None
            self.loss: float = 0

        self.quantum_state: QuantumState = QuantumState()
        self.quantum_state.set_state_single(quantum_state)
        self.qstate_key = None
        self.is_null: bool = False

    def entangle(self, photon):
        """Method to entangle photons (see `QuantumState` module)."""

        self.quantum_state.entangle(photon.quantum_state)

    def random_noise(self, rng: Generator):
        """Method to add random noise to photon's state (see `QuantumState` module)."""

        self.quantum_state.random_noise(rng)

    def set_state(self, state):
        self.quantum_state.set_state(state)

    @staticmethod
    def measure(basis, photon, rng: Generator):
        """Method to measure a photon (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photon.
            photon (Photon): photon to measure.

        Returns:
            int: 0/1 value giving result of measurement in given basis.
        """

        return photon.quantum_state.measure(basis, rng)

    @staticmethod
    def measure_multiple(basis, photons, rng: Generator):
        """Method to measure 2 entangled photons (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photons.
            photons (List[Photon]): list of 2 photons to measure.

        Returns:
            int: 0-3 value giving the result of measurement in given basis.
        """

        return QuantumState.measure_multiple(basis, [photons[0].quantum_state,
                                                     photons[1].quantum_state],
                                             rng)

    def add_loss(self, loss: float):
        assert 0 <= loss <= 1
        assert self.encoding_type["name"] == "single_atom"
        self.loss = 1 - (1 - self.loss) * (1 - loss)
