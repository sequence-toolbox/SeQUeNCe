"""This module defines the quantum manager class, to track quantum states.

The states may currently be defined in two possible ways:
    - KetState (with the QuantumManagerKet class)
    - DensityMatrix (with the QuantumManagerDensity class)

The manager defines an API for interacting with quantum states.
"""
from typing import List, Dict

from .quantum_manager import QuantumManagerKet, QuantumManagerDensity, KetState, DensityState


class ParallelQuantumManagerKet(QuantumManagerKet):
    """Class to track and manage quantum states with the ket vector formalism."""

    def __init__(self, states, least_available):
        super().__init__()
        self.states = states
        self._least_available = least_available

    def new(self, state=(complex(1), complex(0))) -> int:
        key = self._least_available.value

        with self._least_available.get_lock():
            self._least_available.value += 1

        self.states[key] = KetState(state, [key])
        return key

    def run_circuit(self, circuit: "Circuit", keys: List[int]) -> Dict[int, int]:
        ret_dict = super().run_circuit(circuit, keys)
        return ret_dict

    def remove(self, key: int) -> None:
        del self.states[key]


class ParallelQuantumManagerDensity(QuantumManagerDensity):
    """Class to track and manage states with the density matrix formalism."""

    def __init__(self, states, least_available):
        super().__init__()
        self.states = states
        self._least_available = least_available

    def new(self, state=[[complex(1), complex(0)], [complex(0), complex(0)]]) -> int:        
        key = self._least_available.value

        with self._least_available.get_lock():
            self._least_available.value += 1

        self.states[key] = DensityState(state, [key])
        return key

    def run_circuit(self, circuit: "Circuit", keys: List[int]) -> Dict[int, int]:
        ret_dict = super().run_circuit(circuit, keys)
        return ret_dict

    def remove(self, key: int) -> None:
        del self.states[key]

