from functools import lru_cache
from copy import copy
from typing import List, Tuple, TYPE_CHECKING
from math import sqrt

from qutip.qip.circuit import QubitCircuit, Gate
from qutip.qip.operations import gate_sequence_product
from numpy import log2, array, kron, identity, zeros, arange
from numpy.random import random_sample, choice


class QuantumManager():
    """Class to track and manage quantum states.

    All states stored are of a single formalism (by default as a ket vector).

    Attributes:
        states (Dict[int, KetState]): mapping of state keys to quantum state objects.
    """

    def __init__(self):
        self.states = {}
        self._least_available = 0

    def new(self, amplitudes=[complex(1), complex(0)]) -> int:
        """Method to create a new quantum state.

        Args:
            amplitudes (List[complex]): complex amplitudes of new state (default [1, 0]).

        Returns:
            int: key for new state generated.
        """
        
        key = self._least_available
        self._least_available += 1
        self.states[key] = KetState(amplitudes, [key])
        return key

    def get(self, key: int) -> "KetState":
        """Method to get quantum state stored at an index.

        Args:
            key (int): key for quantum state.

        Returns:
            KetState: quantum state at supplied key.
        """
        return self.states[key]

    def run_circuit(self, circuit: "Circuit", keys: List[int]) -> int:
        """Method to run a circuit on a given set of quantum states.
        
        Args:
            circuit (Circuit): quantum circuit to apply.
            keys (List[int]): list of keys for quantum states to apply circuit to.

        Returns:
            int: measurement results.
        """
        assert len(keys) == circuit.size, "mismatch between circuit size and supplied qubits"

        old_states = []
        all_keys = []
        for key in keys:
            qstate = self.states[key]
            if qstate.keys[0] not in all_keys:
                old_states.append(qstate.state)
                all_keys += qstate.keys

        # construct compound state; order qubits
        new_state = [1]
        for state in old_states:
            new_state = kron(state, new_state)

        if not all([all_keys.index(key) == i for i, key in enumerate(keys)]):
            swap_circuit = QubitCircuit(N=len(all_keys))
            for i, key in enumerate(keys):
                j = all_keys.index(key)
                if j != i:
                    gate = Gate("SWAP", targets=[i, j])
                    swap_circuit.add_gate(gate)
                    all_keys[i], all_keys[j] = all_keys[j], all_keys[i]
            swap_mat = gate_sequence_product(swap_circuit.propagators())
            new_state = swap_mat @ new_state
        
        # multiply circuit matrix
        circ_mat = circuit.get_unitary_matrix()
        if circuit.size < len(all_keys):
            # pad size of circuit matrix if necessary
            diff = len(all_keys) - circuit.size
            circ_mat = circ_mat @ identity(diff)
        new_state = circ_mat @ new_state

        # set state
        new_ket = KetState(new_state, all_keys)
        for key in all_keys:
            self.states[key] = new_ket
        
        # measure and return
        if len(circuit.measured_qubits) == 0:
            return None
        else:
            keys = [all_keys[i] for i in circuit.measured_qubits]
            return self._measure(new_state, keys, all_keys)

    def set(self, keys: List[int], amplitudes: List[complex]) -> None:
        """Method to set quantum state at a given key(s).

        Args:
            keys (List[int]): key(s) of state(s) to change.
            amplitudes (List[complex]): List of amplitudes to set state to (should be of length 2 ** len(keys)).
        """

        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of keys"
        num_qubits = int(num_qubits)
        assert num_qubits == len(keys), "Length of amplitudes should be 2 ** n, where n is the number of keys"

        new_state = KetState(amplitudes, keys)
        for key in keys:
            self.states[key] = new_state

    def remove(self, key: int) -> None:
        """Method to remove state stored at key."""
        del self.states[key]

    def _measure(self, state: List[complex], keys: List[int], all_keys: List[int]) -> int:
        """Method to measure qubits at given keys.

        SHOULD NOT be called individually; only from circuit method (unless for unit testing purposes).

        Args:
            keys (List[int]): list of keys to measure

        Returns:
            int: Measurement result. In range 0 to (2 ** len(keys)) 
        """

        if len(keys) == 1:
            if len(all_keys) == 1:
                prob_0 = _measure_state_with_cache(tuple(state))
                if random_sample() < prob_0:
                    new_state = array([1, 0], dtype=complex)
                    result = 0
                else:
                    new_state = array([0, 1], dtype=complex)
                    result = 1

            else:
                key = keys[0]
                num_states = len(all_keys)
                state_index = all_keys.index(key)
                state_0, state_1, prob_0 = _measure_entangled_state_with_cache(tuple(state), state_index, num_states)
                if random_sample() < prob_0:
                    new_state = array(state_0, dtype=complex)
                    result = 0
                else:
                    new_state = array(state_1, dtype=complex)
                    result = 1

            new_state_obj = KetState(new_state, all_keys)

        else:
            # swap states into correct position
            if not all([all_keys.index(key) == i for i, key in enumerate(keys)]):
                swap_circuit = QubitCircuit(N=len(all_keys))
                for i, key in enumerate(keys):
                    j = all_keys.index(key)
                    if j != i:
                        gate = Gate("SWAP", targets=[i, j])
                        swap_circuit.add_gate(gate)
                        all_keys[i], all_keys[j] = all_keys[j], all_keys[i]
                swap_mat = gate_sequence_product(swap_circuit.propagators())
                state = swap_mat @ state

            # calculate meas probabilities and projected states
            len_diff = len(all_keys) - len(keys)
            new_states, probabilities = _measure_multiple_with_cache(tuple(state), len(keys), len_diff)

            # choose result, set as new state
            possible_results = arange(0, 2 ** len(keys), 1)
            result = choice(possible_results, p=probabilities)
            new_state = new_states[result]
            new_state_obj = KetState(new_state, all_keys)

        for key in keys:
            self.states[key] = new_state_obj
        return result
            

class KetState():
    def __init__(self, amplitudes: List[complex], keys: List[int]):
        # check formatting
        assert all([abs(a) <= 1.01 for a in amplitudes]), "Illegal value with abs > 1 in ket vector"
        assert abs(sum([a ** 2 for a in amplitudes]) - 1) < 1e-5, "Squared amplitudes do not sum to 1" 
        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of qubits"
        assert num_qubits == len(keys), "Length of amplitudes should be 2 ** n, where n is the number of qubits"

        self.state = array(amplitudes)
        self.keys = keys


@lru_cache(maxsize=1000)
def _measure_state_with_cache(state: Tuple[complex, complex]) -> float:
    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = (state.conj().transpose() @ M0.conj().transpose() @ M0 @ state).real
    return prob_0


@lru_cache(maxsize=1000)
def _measure_entangled_state_with_cache(state: Tuple[complex], state_index: int, num_states: int) -> Tuple[
        Tuple[complex], Tuple[complex], float]:
    state = array(state)
    # measurement operator
    M0 = array([[1, 0], [0, 0]], dtype=complex)
    M1 = array([[0, 0], [0, 1]], dtype=complex)

    # generate projectors
    projector0 = [1]
    projector1 = [1]
    for i in range(num_states):
        if i == state_index:
            projector0 = kron(M0, projector0)
            projector1 = kron(M1, projector1)
        else:
            projector0 = kron(identity(2), projector0)
            projector1 = kron(identity(2), projector1)

    # probability of measuring basis[0]
    prob_0 = (state.conj().transpose() @ projector0.conj().transpose() @ projector0 @ state).real

    if prob_0 >= 1:
        state1 = None
    else:
        state1 = (projector1 @ state) / sqrt(1 - prob_0)

    if prob_0 <= 0:
        state0 = None
    else:
        state0 = (projector0 @ state) / sqrt(prob_0)

    return (state0, state1, prob_0)


@lru_cache(maxsize=1000)
def _measure_multiple_with_cache(state: Tuple[complex], num_states: int, length_diff: int) -> Tuple[
        Tuple[Tuple[complex]], Tuple[float]]:
    state = array(state)
    basis_count = 2 ** num_states

    # construct measurement operators, projectors, and probabilities of measurement
    projectors = [None] * basis_count
    probabilities = [0] * basis_count
    for i in range(basis_count):
        M = zeros((basis_count, basis_count), dtype=complex)  # measurement operator
        M[i, i] = 1
        projectors[i] = kron(identity(2 ** length_diff), M)  # projector
        probabilities[i] = (state.conj().transpose() @ projectors[i].conj().transpose() @ projectors[i] @ state).real
        if probabilities[i] < 0:
            probabilities[i] = 0
        if probabilities[i] > 1:
            probabilities[i] = 1

    return_states = [None] * len(projectors)
    for i, proj in enumerate(projectors):
        # project to new state
        if probabilities[i] > 0:
            new_state = (proj @ state) / sqrt(probabilities[i])
            new_state = tuple(new_state)
            return_states[i] = new_state

    return (tuple(return_states), tuple(probabilities))
