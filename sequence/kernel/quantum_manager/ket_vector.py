"""
This module implements the quantum manager for ket vector states.
"""
from __future__ import annotations

from .base import QuantumManager, QuantumManagerDenseQubit
from ..quantum_state import KetState, OneDimensionInput
from ..quantum_utils import measure_entangled_state_with_cache_ket, measure_multiple_with_cache_ket, measure_state_with_cache_ket
from ...constants import KET_VECTOR_FORMALISM

from numpy import array
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...components.circuit import Circuit


@QuantumManager.register(KET_VECTOR_FORMALISM)
class QuantumManagerKet(QuantumManagerDenseQubit):
    """Class to track and manage quantum states with the ket vector formalism."""

    def __init__(self):
        super().__init__()

    def new(self, state: OneDimensionInput = (complex(1), complex(0))) -> int:
        """Method to create a new ket state.

        Args:
            state (OneDimensionInput): 1D state-vector amplitudes.

        Returns:
            int: the key of the new state.
        """
        key = self._least_available
        self._least_available += 1
        self.states[key] = KetState(state, [key])
        return key

    def run_circuit(self, circuit: Circuit, keys: list[int], meas_samp=None) -> dict[int, int]:
        """Method to run a circuit on a given list of keys.
        
        Args:
            circuit (Circuit): quantum circuit to apply.
            keys (list[int]): list of keys to apply circuit to.
            meas_samp (float): random sample used for measurement result.
        
        Returns:
            If measurement, dict[int, int]: dictionary mapping qstate keys to measurement results.
            If non-measurement, dict: empty dictionary.
        """
        self._validate_circuit_run(circuit, keys, meas_samp)
        new_state, all_keys, circ_mat = self._prepare_circuit(circuit, keys)

        new_state = circ_mat @ new_state

        if len(circuit.measured_qubits) == 0:
            # set state, return no measurement result
            new_ket = KetState(new_state, all_keys)
            for key in all_keys:
                self.states[key] = new_ket
            return {}
        else:
            # measure state (state reassignment done in _measure method)
            keys = [all_keys[i] for i in circuit.measured_qubits]
            return self._measure(new_state, keys, all_keys, meas_samp)

    def set(self, keys: list[int], amplitudes: OneDimensionInput) -> None:
        """Set the quantum state for the given keys.

        Args:
            keys (list[int]): list of keys of the quantum state.
            amplitudes (OneDimensionInput): amplitudes to set the state to.
        """
        new_state = KetState(amplitudes, keys)
        for key in keys:
            self.states[key] = new_state

    def get_ascending_keys(self, key: int) -> KetState:
        """Method to get quantum state stored at an index.
           Reorders qubits (in-place) in ascending order of keys before returning.

        Args:
            key (int): key for quantum state.

        Returns:
            KetState: quantum state at supplied key.
        """
        state = super().get(key)
        self.reorder_qubits_ascending_keys(state)
        return state

    def reorder_qubits_ascending_keys(self, state: KetState) -> None:
        """Update the quantum state (in-place) to match the ascending order of keys.
           Meanwhile, the reordered state is also set in the quantum manager.
        
        Args:
            state (KetState): The quantum state to reorder.
        """
        target_all_keys = sorted(state.keys)
        if state.keys != target_all_keys:
            _, swap_matrix = self._swap_qubits(state.keys, target_all_keys)
            reordered_state = swap_matrix @ state.state
            state.state = reordered_state
            self.set(target_all_keys, reordered_state.tolist())

    def set_to_zero(self, key: int) -> None:
        """Set the qubit at the given key to the |0> state.

        Args:
            key (int): key of the qubit to set to |0>.
        """
        self.set([key], [complex(1), complex(0)])

    def set_to_one(self, key: int) -> None:
        """Set the qubit at the given key to the |1> state.

        Args:
            key (int): key of the qubit to set to |1>.
        """
        self.set([key], [complex(0), complex(1)])

    def _measure(self, state: list[complex], keys: list[int], all_keys: list[int], meas_samp: float) -> dict[int, int]:
        """Method to measure qubits at given keys.

        SHOULD NOT be called individually; only from circuit method (unless for unit testing purposes).
        Modifies quantum state of all qubits given by all_keys.

        Args:
            state (list[complex]): state to measure.
            keys (list[int]): list of keys to measure.
            all_keys (list[int]): list of all keys corresponding to state.
            meas_samp (float): random number between 0 and 1 used for measurement.

        Returns:
            dict[int, int]: mapping of measured keys to measurement results.
        """
        if len(keys) == 1:
            if len(all_keys) == 1:
                prob_0 = measure_state_with_cache_ket(tuple(state))
                if meas_samp < prob_0:
                    result = 0
                else:
                    result = 1
            else:
                key = keys[0]
                num_states = len(all_keys)
                state_index = all_keys.index(key)
                state_0, state_1, prob_0 = measure_entangled_state_with_cache_ket(tuple(state), state_index, num_states)
                if meas_samp < prob_0:
                    new_state = array(state_0, dtype=complex)
                    result = 0
                else:
                    new_state = array(state_1, dtype=complex)
                    result = 1

            all_keys.remove(keys[0])

        else:
            # swap states into correct position
            if not all([all_keys.index(key) == i for i, key in enumerate(keys)]):
                all_keys, swap_mat = self._swap_qubits(all_keys, keys)
                state = swap_mat @ state

            # calculate meas probabilities and projected states
            len_diff = len(all_keys) - len(keys)
            new_states, probabilities = measure_multiple_with_cache_ket(tuple(state), len(keys), len_diff)

            # choose result, set as new state
            for i in range(int(2 ** len(keys))):
                if meas_samp < sum(probabilities[:i + 1]):
                    result = i
                    new_state = new_states[i]
                    break

            for key in keys:
                all_keys.remove(key)

        result_states = [array([1, 0]), array([0, 1])]
        result_digits = [int(x) for x in bin(result)[2:]]
        while len(result_digits) < len(keys):
            result_digits.insert(0, 0)

        for res, key in zip(result_digits, keys):
            # set to state measured
            new_state_obj = KetState(result_states[res], [key])
            self.states[key] = new_state_obj

        if len(all_keys) > 0:
            new_state_obj = KetState(new_state, all_keys)
            for key in all_keys:
                self.states[key] = new_state_obj

        return dict(zip(keys, result_digits))
