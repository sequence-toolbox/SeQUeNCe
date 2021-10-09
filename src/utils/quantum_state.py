"""Definition of the quantum state class.

This module defines the QuantumState class, used by photons and memories to track internal quantum states.
The class provides interfaces for measurement and entanglement.
"""
from functools import lru_cache
from math import sqrt
from typing import Tuple

from numpy import pi, cos, sin, array, outer, kron, identity, arange
from numpy.random import Generator


def swap_bits(num, pos1, pos2):
    """Swaps bits in num at positions 1 and 2.

    Used by quantum_state.measure_multiple method.
    """

    bit1 = (num >> pos1) & 1
    bit2 = (num >> pos2) & 1
    x = bit1 ^ bit2
    x = (x << pos1) | (x << pos2)
    return num ^ x


class QuantumState():
    """Class to manage a quantum state.

    Tracks quantum state coefficients (in Z-basis) and entangled states.
    Functions related to the randomness uses the provided pseudo random number
    generator (PRNG) to generate random numbers for a reproducible simulation.

    Attributes:
        state (Tuple[complex]): list of complex coefficients in Z-basis.
        entangled_states (List[QuantumState]): list of entangled states (indludng self).
    """

    def __init__(self):
        self.state = (complex(1), complex(0))
        self.entangled_states = [self]

    def entangle(self, another_state: "QuantumState"):
        """Method to entangle two quantum states.

        Arguments:
            another_state (QuantumState): state to entangle current state with.

        Side Effects:
            Modifies the `entangled_states` field for current state and `another_state`.
            Modifies the `state` field for current state and `another_state`.
        """

        entangled_states = self.entangled_states + another_state.entangled_states
        new_state = kron(self.state, another_state.state)
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
        angle = rng.random() * 2 * pi
        self.state = (complex(cos(angle)), complex(sin(angle)))

    # only for use with entangled state
    def set_state(self, state: Tuple[complex]):
        """Method to change entangled state of multiple quantum states.

        Args:
            state (Tuple[complex]): new coefficients for state. Should be 2^n in length, where n is the length of `entangled_states`.

        Side Effects:
            Modifies the `state` field for current and entangled states.
        """

        for qs in self.entangled_states:
            qs.state = state

    # for use with single, unentangled state
    def set_state_single(self, state: Tuple[complex]):
        """Method to unentangle and set the state of a single quantum state object.

        Args:
            state (Tuple[complex]): 2-element list of new complex coefficients.

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

    def measure(self, basis: Tuple[Tuple[complex]], rng: Generator) -> int:
        """Method to measure a single quantum state.

        Args:
            basis (Tuple[Tuple[complex]]): measurement basis, given as list of states (that are themselves lists of complex coefficients).

        Returns:
            int: 0/1 measurement result, corresponding to one basis vector.

        Side Effects:
            Modifies the `state` field for current and any entangled states.
        """

        # handle entangled case
        if len(self.entangled_states) > 1:
            num_states = len(self.entangled_states)
            state_index = self.entangled_states.index(self)
            state0, state1, prob = _measure_entangled_state_with_cache(self.state, basis, state_index, num_states)
            if rng.random() < prob:
                new_state = state0
                result = 0
            else:
                new_state = state1
                result = 1
            new_state = tuple(new_state)

        # handle unentangled case
        else:
            prob = _measure_state_with_cache(self.state, basis)
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
            basis (List[List[complex]]): list of basis vectors.
            states (List[QuantumState]): list of quantum state objects to meausre.

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

        new_states, probabilities = _measure_multiple_with_cache(state, basis, length_diff)

        possible_results = arange(0, basis_dimension, 1)
        # result gives index of the basis vector that will be projected to
        res = rng.choice(possible_results, p=probabilities)
        # project to new state, then reassign quantum state and entangled photons
        new_state = new_states[res]
        for state in entangled_list:
            state.quantum_state = new_state
            state.entangled_photons = entangled_list

        return res


@lru_cache(maxsize=1000)
def _measure_state_with_cache(state: Tuple[complex, complex], basis: Tuple[Tuple[complex]]) -> float:
    state = array(state)
    u = array(basis[0], dtype=complex)
    v = array(basis[1], dtype=complex)
    # measurement operator
    M0 = outer(u.conj(), u)
    M1 = outer(v.conj(), v)

    # probability of measuring basis[0]
    prob_0 = (state.conj().transpose() @ M0.conj().transpose() @ M0 @ state).real
    return prob_0

@lru_cache(maxsize=1000)
def _measure_entangled_state_with_cache(state: Tuple[complex], basis:Tuple[Tuple[complex]],
                                        state_index: int, num_states: int) -> Tuple[
        Tuple[complex], Tuple[complex], float]:
    state = array(state)
    u = array(basis[0], dtype=complex)
    v = array(basis[1], dtype=complex)
    # measurement operator
    M0 = outer(u.conj(), u)
    M1 = outer(v.conj(), v)

    # generate projectors
    projector0 = [1]
    projector1 = [1]
    for i in range(num_states):
        if i == state_index:
            projector0 = kron(projector0, M0)
            projector1 = kron(projector1, M1)
        else:
            projector0 = kron(projector0, identity(2))
            projector1 = kron(projector1, identity(2))

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
def _measure_multiple_with_cache(state: Tuple[Tuple[complex]], basis: Tuple[Tuple[complex]], length_diff: int) -> Tuple[
        Tuple[Tuple[complex]], Tuple[float]]:
    state = array(state)
    # construct measurement operators, projectors, and probabilities of measurement
    projectors = [None] * len(basis)
    probabilities = [0] * len(basis)
    for i, vector in enumerate(basis):
        vector = array(vector, dtype=complex)
        M = outer(vector.conj(), vector)  # measurement operator
        projectors[i] = kron(M, identity(2 ** length_diff))  # projector
        probabilities[i] = (state.conj().transpose() @ projectors[i].conj().transpose() @ projectors[i] @ state).real
        if probabilities[i] < 0:
            probabilities[i] = 0

    return_states = [None] * len(projectors)
    for i, proj in enumerate(projectors):
        # project to new state
        if probabilities[i] > 0:
            new_state = (proj @ state) / sqrt(probabilities[i])
            new_state = tuple(new_state)
            return_states[i] = new_state

    return (tuple(return_states), tuple(probabilities))
