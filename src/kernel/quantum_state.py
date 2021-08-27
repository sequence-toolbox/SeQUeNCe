"""Definition of the quantum state classes.

This module defines the classes used to track quantum states in SeQUeNCe.
These include 2 classes used by a quantum manager, and one used for individual photons:

1. The `KetState` class represents the ket vector formalism and is used by a quantum manager.
2. The `DensityState` class represents the density matrix formalism and is also used by a quantum manager.
3. The `FreeQuantumState` class uses the ket vector formalism, and is used by individual photons (not the quantum manager).
"""

from abc import ABC
from typing import Tuple, List

from numpy import pi, cos, sin, arange, log2
from numpy.random import random, random_sample, choice

from .quantum_utils import *


def swap_bits(num, pos1, pos2):
    """Swaps bits in num at positions 1 and 2.

    Used by quantum_state.measure_multiple method.
    """

    bit1 = (num >> pos1) & 1
    bit2 = (num >> pos2) & 1
    x = bit1 ^ bit2
    x = (x << pos1) | (x << pos2)
    return num ^ x


class State(ABC):
    """Base class for storing quantum states (abstract).

    Attributes:
        state (any): internal representation of the state, may vary by state type.
        entangled_states (List[State]): list of other entangled states, for use when no quantum manager present.
        keys (List[int]): list of keys pointing to the state, for use with a quantum manager.
        valid (List[bool]): list denoting if corresponding key is still in scope.
            If all keys become out of scope, will be removed from state manager.
    """

    def __init__(self):
        super().__init__()

        self.state = None
        self.entangled_states = []
        self.keys = []
        self.valid = []


class KetState(State):
    """Class to represent an individual quantum state as a ket vector.

    Attributes:
        state (np.array): state vector. Should be of length 2 ** len(keys).
        keys (List[int]): list of keys (qubits) associated with this state.
    """

    def __init__(self, amplitudes: List[complex], keys: List[int]):
        super().__init__()

        # check formatting
        assert all([abs(a) <= 1.01 for a in amplitudes]), "Illegal value with abs > 1 in ket vector"
        assert abs(sum([a ** 2 for a in amplitudes]) - 1) < 1e-5, "Squared amplitudes do not sum to 1"
        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of qubits"
        assert num_qubits == len(keys), "Length of amplitudes should be 2 ** n, where n is the number of qubits"

        self.state = array(amplitudes, dtype=complex)
        self.keys = keys
        self.valid = [True] * len(keys)

    def __str__(self):
        return "\n".join(["Keys:", str(self.keys), "State:", str(self.state)])


class DensityState(State):
    """Class to represent an individual quantum state as a density matrix.

    Attributes:
        state (np.array): density matrix values. NxN matrix with N = 2 ** len(keys).
        keys (List[int]): list of keys (qubits) associated with this state.
    """

    def __init__(self, state: List[List[complex]], keys: List[int]):
        super().__init__()

        """Constructor for density state class.

        Args:
            state (List[List[complex]]): density matrix elements given as a list.
                If the list is one-dimensional, will be converted to matrix with outer product operation.
            keys (List[int]): list of keys to this state in quantum manager.
        """

        state = array(state, dtype=complex)
        if state.ndim == 1:
            state = outer(state.conj(), state)

        # check formatting
        assert abs(trace(array(state)) - 1) < 0.1, "density matrix trace must be 1"
        for row in state:
            assert len(state) == len(row), "density matrix must be square"
        num_qubits = log2(len(state))
        assert num_qubits.is_integer(), "Dimensions of density matrix should be 2 ** n, where n is the number of qubits"
        assert num_qubits == len(keys), "Dimensions of density matrix should be 2 ** n, where n is the number of qubits"

        self.state = state
        self.keys = keys
        self.valid = [True] * len(keys)

    def __str__(self):
        return "\n".join(["Keys:", str(self.keys), "State:", str(self.state)])


class FreeQuantumState(State):
    """Class used by photons to track internal quantum states.

    This is an alternative to tracking states in a dedicated quantum manager, which adds simulation overhead.
    It defines several operations, including entanglement and measurement.
    For memories with an internal quantum state and certain photons, such as those stored in a memory or in parallel
    simulation, this class should not be used.
    Quantum states stored in a quantum manager class should be used instead.
    This module uses the ket vector formalism for storing and manipulating states.

    Attributes:
        state (Tuple[complex]): list of complex coefficients in Z-basis.
        entangled_states (List[QuantumState]): list of entangled states (including self).
    """

    def __init__(self):
        super().__init__()
        self.state = (complex(1), complex(0))
        self.entangled_states = [self]

    def entangle(self, another_state: "FreeQuantumState"):
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

    def random_noise(self):
        """Method to add random noise to a single state.

        Chooses a random angle to set the quantum state to (with no phase difference).

        Side Effects:
            Modifies the `state` field.
        """

        # TODO: rewrite for entangled states
        angle = random() * 2 * pi
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

    def measure(self, basis: Tuple[Tuple[complex]]) -> int:
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
            state0, state1, prob = measure_entangled_state_with_cache(self.state, basis, state_index, num_states)
            if random_sample() < prob:
                new_state = state0
                result = 0
            else:
                new_state = state1
                result = 1
            new_state = tuple(new_state)

        # handle unentangled case
        else:
            prob = measure_state_with_cache(self.state, basis)
            if random_sample() < prob:
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
    def measure_multiple(basis, states):
        """Method to measure multiple qubits in a more complex basis.

        May be used for bell state measurement.

        Args:
            basis (List[List[complex]]): list of basis vectors.
            states (List[QuantumState]): list of quantum state objects to measure.

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

        possible_results = arange(0, basis_dimension, 1)
        # result gives index of the basis vector that will be projected to
        res = choice(possible_results, p=probabilities)
        # project to new state, then reassign quantum state and entangled photons
        new_state = new_states[res]
        for state in entangled_list:
            state.quantum_state = new_state
            state.entangled_photons = entangled_list

        return res
