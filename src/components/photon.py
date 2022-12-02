"""Model for single photon.

This module defines the Photon class for tracking individual photons.
Photons may be encoded directly with polarization or time bin schemes, or may herald the encoded state of single atom memories.
"""
from typing import Dict, Any, List, Union, TYPE_CHECKING
from numpy import log2

if TYPE_CHECKING:
    from numpy.random._generator import Generator
    from ..kernel.timeline import Timeline
    from ..kernel.entity import Entity
    from ..kernel.quantum_state import State

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
        quantum_state (Union[int, Tuple[complex]]): quantum state of photon.
            If `use_qm` is false, this will be a QuantumState object.
            Otherwise, it will be an integer key for the quantum manager.
        is_null (bool): defines whether photon is real or a "ghost" photon (not detectable but used in memory encoding).
        loss (float): similarly defined for memory encoding, used to track loss and improve performance.
            Does not need to be utilized for all encoding schemes.
        use_qm (bool): determines if photon stores state locally (False) or uses timeline quantum manager (True).

    Note: the `loss` attribute is currently specifically used for the `"single_atom"` encoding scheme.
    This encoding scheme also removes the local timeline reference and sets the quantum state to the local key.
    This is to both facilitate parallel execution and improve the performance of overall simulation.
    """

    _entangle_circuit = Circuit(2)
    _measure_circuit = Circuit(1)
    _measure_circuit.measure(0)

    def __init__(self, name: str, timeline: "Timeline", wavelength=0, location=None, encoding_type=polarization,
                 quantum_state=None, use_qm=False):
        """Constructor for the photon class.

        Args:
            name (str): name of the photon instance.
            timeline (Timeline): simulation timeline reference
            wavelength (int): wavelength of photon (in nm) (default 0).
            location (Entity): location of the photon (default None).
            encoding_type (Dict[str, Any]): encoding type of photon (from encoding module) (default polarization).
            quantum_state (Union[int, Tuple[complex]]):
                reference key for quantum manager, or complex coefficients for photon's quantum state.
                Default state is (1, 0).
                If left blank and `use_qm` is true, will create new key from timeline quantum manager.
            use_qm (bool): determines if the quantum state is obtained from the quantum manager or stored locally.
        """

        if encoding_type["name"] == "absorptive" and not use_qm:
            raise ValueError("Photons with 'absorptive' encoding scheme must use quantum manager.")

        self.name: str = name
        self.timeline = timeline
        self.wavelength: int = wavelength
        self.location: Entity = location
        self.encoding_type: Dict[str, Any] = encoding_type
        self.is_null: bool = False
        self.loss: float = 0
        self.use_qm = use_qm

        self.quantum_state: Union[State, int] = -1
        if self.use_qm:
            if quantum_state is None:
                self.quantum_state = timeline.quantum_manager.new()
            else:
                assert type(quantum_state) is int
                self.quantum_state = quantum_state
        else:
            if quantum_state is None:
                quantum_state = (complex(1), complex(0))
            else:
                assert type(quantum_state) is tuple
                assert all([abs(a) <= 1.01 for a in quantum_state]), "Illegal value with abs > 1 in photon state"
                assert abs(sum([abs(a) ** 2 for a in quantum_state]) - 1) < 1e-5, "Squared amplitudes do not sum to 1"
                num_qubits = log2(len(quantum_state))
                assert num_qubits == 1, "Length of amplitudes for single photon should be 2"
            self.quantum_state = FreeQuantumState()
            self.quantum_state.state = quantum_state

    def __del__(self):
        if self.use_qm and self.timeline is not None:
            self.timeline.quantum_manager.remove(self.quantum_state)

    def combine_state(self, photon):
        """Method to combine quantum states of photons (see `QuantumState` module).

        This method does not modify the current state of the photon, but combines the internal quantum state object.
        This ensures that two photons share a quantum state object describing a product space.
        """

        if self.use_qm:
            qm = self.timeline.quantum_manager
            all_keys = qm.get(self.quantum_state).keys + \
                self.timeline.quantum_manager.get(photon.quantum_state).keys
            qm.run_circuit(Photon._entangle_circuit, all_keys)
        else:
            self.quantum_state.combine_state(photon.quantum_state)

    def random_noise(self, rng: "Generator"):
        """Method to add random noise to photon's state (see `QuantumState` module)."""

        self.quantum_state.random_noise(rng)

    def set_state(self, state):
        if self.use_qm:
            qm = self.timeline.quantum_manager
            all_keys = qm.get(self.quantum_state).keys
            self.timeline.quantum_manager.set(all_keys, state)
        else:
            self.quantum_state.set_state(state)

    @staticmethod
    def measure(basis, photon: "Photon", rng: "Generator"):
        """Method to measure a photon (see `QuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photon.
            photon (Photon): photon to measure.
            rng (Generator): PRNG to use for measurement results.

        Returns:
            int: 0/1 value giving result of measurement in given basis.
        """

        if photon.use_qm:
            qm = photon.timeline.quantum_manager
            key = photon.quantum_state
            all_keys = qm.get(key).keys
            meas_samp = rng.random()

            # see if we don't need rearranging:
            if len(all_keys) == 1 or all_keys.index(key) == 0:
                res = qm.run_circuit(Photon._measure_circuit, [key], meas_samp)
            # if we do, run bigger circuit to save time swapping
            else:
                circuit = Circuit(len(all_keys))
                circuit.measure(all_keys.index(key))
                res = qm.run_circuit(circuit, all_keys, meas_samp)

            return res[photon.quantum_state]

        else:
            return photon.quantum_state.measure(basis, rng)

    @staticmethod
    def measure_multiple(basis, photons: List["Photon"], rng: "Generator"):
        """Method to measure 2 entangled photons (see `FreeQuantumState` module).

        Args:
            basis (List[List[complex]]): basis (given as lists of complex coefficients) with which to measure the photons.
            photons (List[Photon]): list of 2 photons to measure.
            rng (Generator): PRNG to use for measurement results.

        Returns:
            int: 0-3 value giving the result of measurement in given basis.
        """

        assert len(photons) == 2, "Photon.measure_multiple() must be called on two photons only."
        if photons[0].use_qm:
            raise NotImplementedError("Photon.measure_multiple() not implemented for quantum manager.")

        return FreeQuantumState.measure_multiple(basis,
                                                 [photons[0].quantum_state, photons[1].quantum_state],
                                                 rng)

    def add_loss(self, loss: float):
        assert 0 <= loss <= 1
        assert self.encoding_type["name"] == "single_atom"
        self.loss = 1 - (1 - self.loss) * (1 - loss)
