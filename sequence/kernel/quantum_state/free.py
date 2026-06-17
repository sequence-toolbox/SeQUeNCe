"""The free quantum state formalism is used by photons and not managed by a dedicated quantum manager."""

import numpy as np
from numpy.random import Generator

from .base import State
from ..quantum_utils import measure_state_with_cache, measure_entangled_state_with_cache, measure_multiple_with_cache


def swap_bits(num, pos1, pos2):
    """Swaps bits in num at positions 1 and 2.

    Used by FreeQuantumState.measure_multiple method.
    """

    bit1 = (num >> pos1) & 1
    bit2 = (num >> pos2) & 1
    x = bit1 ^ bit2
    x = (x << pos1) | (x << pos2)
    return num ^ x


class FreeQuantumState(State):
    """Class used by photons to track internal quantum states.

    This is an alternative to tracking states in a dedicated quantum manager, which adds simulation overhead.
    It defines several operations, including entanglement and measurement.
    For memories with an internal quantum state and certain photons, such as those stored in a memory or in parallel
    simulation, this class should not be used.
    Quantum states stored in a quantum manager class should be used instead.
    This module uses the ket vector formalism for storing and manipulating states.

    Attributes:
        state (tuple[complex]): list of complex coefficients in Z-basis.
        entangled_states (list[QuantumState]): list of entangled states (including self).
    """

    def __init__(self):
        super().__init__()
        self.state = (complex(1), complex(0))
        self.entangled_states = [self]

    def combine_state(self, another_state: "FreeQuantumState"):
        """Method to tensor multiply two quantum states.

        Arguments:
            another_state (QuantumState): state to entangle current state with.

        Side Effects:
            Modifies the `entangled_states` field for current state and `another_state`.
            Modifies the `state` field for current state and `another_state`.
        """

        entangled_states = self.entangled_states + another_state.entangled_states
        new_state = np.kron(self.state, another_state.state)
        new_state = tuple(new_state)

        for quantum_state in entangled_states:
            quantum_state.entangled_states = entangled_states
            quantum_state.state = new_state

    def random_noise(self, rng: Generator):
        """Method to add random noise to a single state.

        Chooses a random angle to set the quantum state to (with no phase difference).

        Side Effects:
            Modifies the `state` field.
        """

        # TODO: rewrite for entangled states
        angle = rng.random() * 2 * np.pi
        self.state = (complex(np.cos(angle)), complex(np.sin(angle)))

    # only for use with entangled state
    def set_state(self, state: tuple[complex]):
        """Method to change entangled state of multiple quantum states.

        Args:
            state (tuple[complex]): new coefficients for state.
                Should be 2^n in length, where n is the length of `entangled_states`.

        Side Effects:
            Modifies the `state` field for current and entangled states.
        """

        # check formatting of state
        assert all([abs(a) <= 1.01 for a in state]), "Illegal value with abs > 1 in quantum state"
        assert abs(sum([abs(a) ** 2 for a in state]) - 1) < 1e-5, "Squared amplitudes do not sum to 1"

        num_qubits = np.log2(len(state))
        assert 2 ** int(round(num_qubits)) == len(state), (
            "Length of amplitudes should be 2 ** n, where n is the number of qubits. "
            f"Actual amplitude length: {len(state)}, num qubits: {num_qubits}")
        num_qubits = int(round(num_qubits))
        assert num_qubits == len(self.entangled_states), (
            "Length of amplitudes should be 2 ** n, where n is the number of qubits. "
            f"Num qubits in state: {num_qubits}, num qubits in object: {len(self.entangled_states)}")

        for qs in self.entangled_states:
            qs.state = state

    # for use with single, unentangled state
    def set_state_single(self, state: tuple[complex]):
        """Method to unentangle and set the state of a single quantum state object.

        Args:
            state (tuple[complex]): 2-element list of new complex coefficients.

        Side Effects:
            Will remove current state from any entangled states (if present).
            Modifies the `state` field of current state.
        """

        for qs in self.entangled_states:
            if qs is not None and qs != self:
                index = qs.entangled_states.index(self)
                qs.entangled_states[index] = None
        self.entangled_states = [self]
        self.state = state

    def measure(self, basis: tuple[tuple[complex]], rng: Generator) -> int:
        """Method to measure a single quantum state.

        Args:
            basis (tuple[tuple[complex]]): measurement basis, given as list of states
                (that are themselves lists of complex coefficients).
            rng (Generator): random number generator for measurement

        Returns:
            int: 0/1 measurement result, corresponding to one basis vector.

        Side Effects:
            Modifies the `state` field for current and any entangled states.
        """

        # handle entangled case
        if len(self.entangled_states) > 1:
            num_states = len(self.entangled_states)
            state_index = self.entangled_states.index(self)
            state0, state1, prob = measure_entangled_state_with_cache(self.state, basis, state_index, num_states)
            if rng.random() < prob:
                new_state = state0
                result = 0
            else:
                new_state = state1
                result = 1
            new_state = tuple(new_state)

        # handle unentangled case
        else:
            prob = measure_state_with_cache(self.state, basis)
            if rng.random() < prob:
                new_state = basis[0]
                result = 0
            else:
                new_state = basis[1]
                result = 1

        # set new state
        # new_state = tuple(new_state)
        for s in self.entangled_states:
            if s is not None:
                s.state = new_state

        return result

    @staticmethod
    def measure_multiple(basis, states, rng: Generator):
        """Method to measure multiple qubits in a more complex basis.

        May be used for bell state measurement.

        Args:
            basis (list[list[complex]]): list of basis vectors.
            states (list[QuantumState]): list of quantum state objects to measure.
            rng (Generator): random number generator for measurement

        Returns:
            int: measurement result in given basis.

        Side Effects:
            Will modify the `state` field of all entangled states.
        """

        # ensure states are entangled
        # (must be entangled prior to calling measure_multiple)
        entangled_list = states[0].entangled_states
        for state in states[1:]:
            assert state in states[0].entangled_states
        # ensure basis and vectors in basis are the right size
        basis_dimension = 2 ** len(states)
        assert len(basis) == basis_dimension
        for vector in basis:
            assert len(vector) == len(basis)

        state = states[0].state

        # move states to beginning of entangled list and quantum state
        pos_state_0 = entangled_list.index(states[0])
        pos_state_1 = entangled_list.index(states[1])
        entangled_list[0], entangled_list[pos_state_0] = entangled_list[pos_state_0], entangled_list[0]
        entangled_list[1], entangled_list[pos_state_1] = entangled_list[pos_state_1], entangled_list[1]
        switched_state = [complex(0)] * len(state)
        for i, coefficient in enumerate(state):
            switched_i = swap_bits(i, pos_state_0, pos_state_1)
            switched_state[switched_i] = coefficient

        state = tuple(switched_state)

        # math for probability calculations
        length_diff = len(entangled_list) - len(states)

        new_states, probabilities = measure_multiple_with_cache(state, basis, length_diff)

        possible_results = np.arange(0, basis_dimension, 1)
        # result gives index of the basis vector that will be projected to
        res = rng.choice(possible_results, p=probabilities)
        # project to new state, then reassign quantum state and entangled photons
        new_state = new_states[res]
        for quantum_state in entangled_list:
            quantum_state.state = new_state
            quantum_state.entangled_states = entangled_list

        return res
