"""This module defines functions and objects to manipulate quantum states.

This includes cached measurement of quantum states, and certain useful operators.
These should not be used directly, but accessed by a QuantumManager instance or by a quantum state.
"""

from functools import lru_cache
from typing import Tuple
from math import sqrt

from numpy import array, kron, identity, zeros, trace, outer, eye


a = array([[0, 1], [0, 0]])
a_dag = array([[0, 0], [1, 0]])

povm_0 = (1/2) * (kron(a_dag @ a, eye(2)) - 1j*kron(a, a_dag) + 1j*kron(a_dag, a) + kron(eye(2), a_dag @ a))
povm_1 = (1/2) * (kron(a_dag @ a, eye(2)) + 1j*kron(a, a_dag) - 1j*kron(a_dag, a) + kron(eye(2), a_dag @ a))


@lru_cache(maxsize=1000)
def measure_state_with_cache(state: Tuple[complex, complex], basis: Tuple[Tuple[complex]]) -> float:
    state = array(state)
    u = array(basis[0], dtype=complex)
    # measurement operator
    M0 = outer(u.conj(), u)

    # probability of measuring basis[0]
    prob_0 = (state.conj().transpose() @ M0.conj().transpose() @ M0 @ state).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache(state: Tuple[complex], basis: Tuple[Tuple[complex]],
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

    return state0, state1, prob_0


@lru_cache(maxsize=1000)
def measure_multiple_with_cache(state: Tuple[complex], basis: Tuple[Tuple[complex]], length_diff: int) \
        -> Tuple[Tuple[Tuple[complex]], Tuple[float]]:
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

    return tuple(return_states), tuple(probabilities)


@lru_cache(maxsize=1000)
def measure_state_with_cache_ket(state: Tuple[complex, complex]) -> float:
    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = (state.conj().T @ M0 @ state).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_ket(state: Tuple[complex], state_index: int, num_states: int) -> Tuple[
        Tuple[complex], Tuple[complex], float]:
    state = array(state)

    # generate projectors
    projector0 = [1]
    projector1 = [1]
    for i in range(num_states):
        if i == state_index:
            projector0 = kron(projector0, [1, 0])
            projector1 = kron(projector1, [0, 1])
        else:
            projector0 = kron(projector0, identity(2))
            projector1 = kron(projector1, identity(2))

    # probability of measuring basis[0]
    prob_0 = (state.conj().T @ projector0.T @ projector0 @ state).real

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
def measure_multiple_with_cache_ket(state: Tuple[complex], num_states: int, length_diff: int) -> Tuple[
        Tuple[Tuple[complex]], Tuple[float]]:
    state = array(state)
    basis_count = 2 ** num_states

    # construct measurement operators, projectors, and probabilities of measurement
    projectors = [None] * basis_count
    probabilities = [0] * basis_count
    for i in range(basis_count):
        M = zeros((1, basis_count), dtype=complex)  # measurement operator
        M[0, i] = 1
        projectors[i] = kron(M, identity(2 ** length_diff))  # projector
        probabilities[i] = (state.conj().T @ projectors[i].T @ projectors[i] @ state).real
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


@lru_cache(maxsize=1000)
def measure_state_with_cache_density(state: Tuple[Tuple[complex, complex]]) -> float:
    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = trace(state @ M0).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_density(state: Tuple[Tuple[complex]], state_index: int, num_states: int) -> Tuple[
        Tuple[complex], Tuple[complex], float]:
    state = array(state)

    # generate projectors
    projector0 = [1]
    projector1 = [1]
    for i in range(num_states):
        if i == state_index:
            projector0 = kron(projector0, [[1, 0], [0, 0]])
            projector1 = kron(projector1, [[0, 0], [0, 1]])
        else:
            projector0 = kron(projector0, identity(2))
            projector1 = kron(projector1, identity(2))

    # probability of measuring basis[0]
    prob_0 = trace(state @ projector0).real

    if prob_0 >= 1:
        state1 = None
    else:
        state1 = (projector1 @ state @ projector1) / (1 - prob_0)

    if prob_0 <= 0:
        state0 = None
    else:
        state0 = (projector0 @ state @ projector0) / prob_0

    return (state0, state1, prob_0)


@lru_cache(maxsize=1000)
def measure_multiple_with_cache_density(state: Tuple[Tuple[complex]], num_states: int, length_diff: int) -> Tuple[
        Tuple[Tuple[complex]], Tuple[float]]:
    state = array(state)
    basis_count = 2 ** num_states

    # construct measurement operators, projectors, and probabilities of measurement
    projectors = [None] * basis_count
    probabilities = [0] * basis_count
    for i in range(basis_count):
        M = zeros((basis_count, basis_count), dtype=complex)  # measurement operator
        M[i, i] = 1
        projectors[i] = kron(M, identity(2 ** length_diff))  # projector
        probabilities[i] = trace(state @ projectors[i]).real
        if probabilities[i] < 0:
            probabilities[i] = 0
        if probabilities[i] > 1:
            probabilities[i] = 1

    return_states = [None] * len(projectors)
    for i, proj in enumerate(projectors):
        # project to new state
        if probabilities[i] > 0:
            new_state = (proj @ state @ proj) / probabilities[i]
            new_state = tuple(new_state)
            return_states[i] = new_state

    return (tuple(return_states), tuple(probabilities))

