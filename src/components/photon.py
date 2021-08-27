"""Model for single photon.

This module defines the Photon class for tracking individual photons.
Photons may be encoded directly with polarization or time bin schemes, or may herald the encoded state of single atom memories.
"""
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from ..components.circuit import Circuit
from ..utils.encoding import polarization
from ..kernel.quantum_state import FreeQuantumState


class Photon:
    """Class for a single photon.

    Attributes:
        name (str): label for photon instance.
        wavelength (float): wavelength of photon (in nm).
        location (Entity): current location of photon.
        encoding_type (Dict[str, Any]): encoding type of photon (as defined in encoding module).
        quantum_state (Any): quantum state of photon.
            If use_qm is false, this will be a QuantumState object. Otherwise, it will be an integer key for the quantum manager.
        is_null (bool): defines whether photon is real or a "ghost" photon (not detectable but used in memory encoding).
        use_qm (bool): determines if photon stores state locally (False) or uses timeline quantum manager (True).
    """

    _entangle_circuit = Circuit(2)
    _measure_circuit = Circuit(1)
    _measure_circuit.measure(0)

    def __init__(self, name: str, timeline: "Timeline", wavelength=0, location=None, encoding_type=polarization,
                 quantum_state=(complex(1), complex(0)), use_qm=False):
        """Constructor for the photon class.

        Args:
            name (str): name of the photon instance.
            timeline (Timeline): simulation timeline reference
            wavelength (int): wavelength of photon (in nm) (default 0).
            location (Entity): location of the photon (default None).
            encoding_type (Dict[str, Any]): encoding type of photon (from encoding module) (default polarization).
            quantum_state (Tuple[complex]): complex coefficients for photon's quantum state (default [1, 0]).
            use_qm (bool): determines if the quantum state is obtained from the quantum manager or stored locally.
        """

        if encoding_type["name"] == "absorptive" and not use_qm:
            raise ValueError("Photons with 'absorptive' encoding scheme must use quantum manager.")

        self.name = name
        self.timeline = timeline
        self.wavelength = wavelength
        self.location = location
        self.encoding_type = encoding_type
        self.is_null = False
        self.use_qm = use_qm

        # if self.encoding_type["name"] == "single_atom":
        #     self.memory = None
        self.quantum_state = None
        if self.use_qm:
            self.quantum_state = timeline.quantum_manager.new()
        else:
            self.quantum_state = FreeQuantumState()
            self.quantum_state.state = quantum_state

    def __del__(self):
        if self.use_qm:
            self.timeline.quantum_manager.remove(self.quantum_state)

    def entangle(self, photon):
        """Method to entangle photons (see `QuantumState` module).

        This method does not modify the current state of the photon, but combines the internal quantum state object.
        This ensures that two photons share a quantum state object.
        """

        if self.use_qm:
            qm = self.timeline.quantum_manager
            all_keys = qm.get(self.quantum_state).keys + \
                self.timeline.quantum_manager.get(photon.quantum_state).keys
            qm.run_circuit(Photon._entangle_circuit, all_keys)
        else:
            self.quantum_state.entangle(photon.quantum_state)

    def random_noise(self):
        """Method to add random noise to photon's state (see `QuantumState` module)."""

        self.quantum_state.random_noise()

    def set_state(self, state):
        if self.use_qm:
            qm = self.timeline.quantum_manager
            all_keys = qm.get(self.quantum_state).keys
            self.timeline.quantum_manager.set(all_keys, state)
        else:
            self.quantum_state.set_state(state)

    @staticmethod
    def measure(basis, photon: "Photon"):
        """Method to measure a photon (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photon.
            photon (Photon): photon to measure.

        Returns:
            int: 0/1 value giving result of measurement in given basis.
        """

        if photon.use_qm:
            qm = photon.timeline.quantum_manager
            key = photon.quantum_state
            all_keys = qm.get(key).keys

            # see if we don't need rearranging:
            if len(all_keys) == 1 or all_keys.index(key) == 0:
                res = qm.run_circuit(Photon._measure_circuit, [key])
            # if we do, run bigger circuit to save time swapping
            else:
                circuit = Circuit(len(all_keys))
                circuit.measure(all_keys.index(key))
                res = qm.run_circuit(circuit, all_keys)

            return res[photon.quantum_state]

        else:
            return photon.quantum_state.measure(basis)

    @staticmethod
    def measure_multiple(basis, photons: List["Photon"]):
        """Method to measure 2 entangled photons (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photons.
            photons (List[Photon]): list of 2 photons to measure.

        Returns:
            int: 0-3 value giving the result of measurement in given basis.
        """

        assert len(photons) == 2, "Photon.measure_multiple() must be called on two photons only."
        if photons[0].use_qm:
            raise NotImplementedError("Photon.measure_multiple() not implemented for quantum manager.")

        return FreeQuantumState.measure_multiple(basis, [photons[0].quantum_state, photons[1].quantum_state])
