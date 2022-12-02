"""This module defines the quantum manager class, to track quantum states.

The states may currently be defined in two possible ways:
    - KetState (with the QuantumManagerKet class)
    - DensityMatrix (with the QuantumManagerDensity class)

The manager defines an API for interacting with quantum states.
"""
from typing import List, Dict, TYPE_CHECKING
from sequence.kernel.quantum_manager import QuantumManagerKet, QuantumManagerDensity

if TYPE_CHECKING:
    from sequence.components.circuit import Circuit


class ParallelQuantumManagerKet(QuantumManagerKet):
    """Class to track and manage quantum states with the ket vector formalism."""

    def __init__(self, states):
        super().__init__()
        self.states = states

    def run_circuit(self, circuit: "Circuit", keys: List[int],
                    meas_samp=None) -> Dict[int, int]:
        ret_dict = super().run_circuit(circuit, keys, meas_samp)
        return ret_dict

    def remove(self, key: int) -> None:
        del self.states[key]


class ParallelQuantumManagerDensity(QuantumManagerDensity):
    """Class to track and manage states with the density matrix formalism."""

    def __init__(self, states):
        super().__init__()
        self.states = states

    def run_circuit(self, circuit: "Circuit", keys: List[int],
                    meas_samp=None) -> Dict[int, int]:
        ret_dict = super().run_circuit(circuit, keys, meas_samp)
        return ret_dict

    def remove(self, key: int) -> None:
        del self.states[key]
