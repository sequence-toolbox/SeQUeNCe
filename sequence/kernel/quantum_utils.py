"""This module defines functions and objects to manipulate quantum states.

This includes cached measurement of quantum states, and certain useful operators.
These should not be used directly, but accessed by a QuantumManager instance or by a quantum state.
"""

from functools import lru_cache
from math import sqrt
import random
import math
from numpy import array, kron, identity, zeros, trace, outer, eye
from scipy.linalg import sqrtm
from ..constants import EPSILON


a = array([[0, 1], [0, 0]])
a_dag = array([[0, 0], [1, 0]])

povm_0 = (1/2) * (kron(a_dag @ a, eye(2)) - 1j*kron(a, a_dag) + 1j*kron(a_dag, a) + kron(eye(2), a_dag @ a))
povm_1 = (1/2) * (kron(a_dag @ a, eye(2)) + 1j*kron(a, a_dag) - 1j*kron(a_dag, a) + kron(eye(2), a_dag @ a))


@lru_cache(maxsize=1000)
def measure_state_with_cache(state: tuple[complex, complex], basis: tuple[tuple[complex]]) -> float:

    state = array(state)
    u = array(basis[0], dtype=complex)
    # measurement operator
    M0 = outer(u.conj(), u)

    # probability of measuring basis[0]
    prob_0 = (state.conj().transpose() @ M0.conj().transpose() @ M0 @ state).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache(state: tuple[complex], basis: tuple[tuple[complex]], state_index: int, num_states: int) \
        -> tuple[array, array, float]:

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
def measure_multiple_with_cache(state: tuple[complex], basis: tuple[tuple[complex]], length_diff: int) \
        -> tuple[list[array], list[float]]:

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
            return_states[i] = new_state

    return return_states, probabilities


@lru_cache(maxsize=1000)
def measure_state_with_cache_ket(state: tuple[complex, complex]) -> float:

    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = (state.conj().T @ M0 @ state).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_ket(state: tuple[complex], state_index: int, num_states: int) \
        -> tuple[array, array, float]:

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

    return state0, state1, prob_0


@lru_cache(maxsize=1000)
def measure_multiple_with_cache_ket(state: tuple[complex], num_states: int, length_diff: int) \
        -> tuple[list[array], list[float]]:

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

    return return_states, probabilities


@lru_cache(maxsize=1000)
def measure_state_with_cache_density(state: tuple[tuple[complex, complex]]) -> float:

    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = trace(state @ M0).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_density(state: tuple[tuple[complex]], state_index: int, num_states: int) \
        -> tuple[array, array, float]:

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

    return state0, state1, prob_0


@lru_cache(maxsize=1000)
def measure_multiple_with_cache_density(state: tuple[tuple[complex]], num_states: int, length_diff: int) \
        -> tuple[list[array], list[float]]:

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

    return return_states, probabilities


@lru_cache(maxsize=1000)
def measure_state_with_cache_fock_density(state: tuple[tuple[complex]], povms: tuple[tuple[tuple[complex]]]) \
        -> tuple[list[array], list[float]]:
    state = array(state)
    povms = [array(povm) for povm in povms]

    # probabilities of getting different outcomes according to POVM operators
    prob_list = [trace(state @ povm).real for povm in povms]
    state_list = []

    # get output states
    for i in range(len(prob_list)):
        if prob_list[i] <= 0:
            state_post_meas = None
        else:
            measure_op = sqrtm(povms[i])
            state_post_meas = (measure_op @ state @ measure_op) / prob_list[i]

        state_list.append(state_post_meas)

    return state_list, prob_list


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_fock_density(state: tuple[tuple[complex]], system_index: int, num_systems: int,
                                                    povms: tuple[tuple[tuple[complex]]], truncation: int = 1) \
        -> tuple[list[array], list[float]]:

    """Measure one subsystem of a larger composite system.

    The measurement SHOULD NOT be entangling measurement, and thus POVM operators should be precisely consisted of
    operators on the subsystem's Hilbert space alone.

    Args:
        state (tuple[tuple[complex]]): state to measure
        system_index (int): index of measured subsystem within state.
        num_systems (int): number of total systems in the state.
        povms (tuple[tuple[tuple[complex]]]): tuple listing all POVM operators to use for measurement
        truncation (int): fock space truncation, 1 for qubit system (default 1).

    Returns:
        tuple[list[array], list[float]]: tuple with two sub-lists.
            The first lists each output state, corresponding with the measurement of each POVM.
            The second lists the probability for each measurement.
    """

    state = array(state)
    povms = [array(povm) for povm in povms]

    # generate POVM operators on total Hilbert space
    povm_list = []
    left_dim = (truncation + 1) ** system_index
    right_dim = (truncation + 1) ** (num_systems - system_index - 1)
    for povm in povms:
        povm_tot = kron(kron(identity(left_dim), povm), identity(right_dim))
        povm_list.append(povm_tot)

    # list of probabilities of getting different outcomes from POVM
    prob_list = [trace(state @ povm).real for povm in povm_list]
    state_list = []

    for i in range(len(prob_list)):
        if prob_list[i] <= 0:
            state_post_meas = None
        else:
            measure_op = sqrtm(povm_list[i])
            state_post_meas = (measure_op @ state @ measure_op) / prob_list[i]

        state_list.append(state_post_meas)

    return state_list, prob_list


@lru_cache(maxsize=1000)
def measure_multiple_with_cache_fock_density(state: tuple[tuple[complex]], indices: tuple[int], num_systems: int,
                                             povms: tuple[tuple[tuple[complex]]], truncation: int = 1) \
        -> tuple[list[array], list[float]]:

    """Measure multiple subsystems of a larger composite system.

    Should be called by Quantum Managers.
    This function will facilitate entangling measurement, e.g. BSM with two photon detectors behind a beamsplitter.
    Such measurement operators are consisted of mixed operators on different subsystems' Hilbert spaces.
    For current implementation, the Hilbert space on which those mixed operators act on is separated from the rest of
    the total Hilbert space, and we assume that the involved subsystems have already been moved close in terms of keys.
    i.e., elements in `indices` argument are no less than 0 and no greater than `num_systems`
    (relative indices w.r.t. the measured state), and the elements MUST BE consecutive.

    E.g. For a total system consisted of 4 subsystems (0, 1, 2, 3) each with dimension d,
    if the entangling measurement happens on (1, 2), then measurement operators on total space will be constructed as
        O_tot = kron(kron(identity(d), O), identity(d)),
    where the measurement operator on (1, 2) subspace needs to be generated beforehand to feed in the function.

    Args:
        state (tuple[tuple[complex]]): state to measure.
        indices (tuple[int]): indices within combined state to measure.
        num_systems (int): number of total systems in the state.
        povms (tuple[tuple[tuple[complex]]]): tuple listing all POVM operators to use for measurement.
        truncation (int): fock space truncation, 1 for qubit system (default 1).

    Returns:
        tuple[list[array], list[float]]: tuple with two sub-lists.
            The first lists each output state, corresponding with the measurement of each POVM.
            The second lists the probability for each measurement.
    """

    state = array(state)
    povms = [array(povm) for povm in povms]

    # judge if elements in `indices` are consecutive
    init_meas_sys_idx = min(indices)
    fin_meas_sys_idx = max(indices)
    num = len(indices)
    if (fin_meas_sys_idx - init_meas_sys_idx + 1 != num) or (list(indices) != sorted(indices)):
        raise ValueError("Indices should be consecutive; got {}".format(indices))

    povm_list = []
    left_dim = (truncation + 1) ** init_meas_sys_idx
    right_dim = (truncation + 1) ** (num_systems - fin_meas_sys_idx - 1)
    for povm in povms:
        povm_tot = kron(kron(identity(left_dim), povm), identity(right_dim))
        povm_list.append(povm_tot)

    # list of probabilities of getting different outcomes from POVM
    prob_list = [trace(state @ povm).real for povm in povm_list]
    state_list = []

    for i in range(len(prob_list)):
        if prob_list[i] <= 0:
            state_post_meas = None
        else:
            measure_op = sqrtm(povm_list[i])
            state_post_meas = (measure_op @ state @ measure_op) / prob_list[i]

        state_list.append(state_post_meas)

    # return post-measurement states and measurement outcome probabilities in the order of fed-in POVM operators
    return state_list, prob_list


@lru_cache(maxsize=1000)
def density_partial_trace(state: tuple[tuple[complex]], indices: tuple[int], num_systems: int, truncation: int = 1) \
        -> array:

    """Traces out subsystems systems at given indices.

    Args:
        state (tuple[tuple[complex]]: input state.
        indices (tuple[int]): indices of subsystems to trace out of state.
            should be sorted in increasing order.
        num_systems (int): number of total subsystems in the state.
        truncation (int): fock space truncation, 1 for qubit system (default 1).

    Returns:
        array: output state with reduced number of subsystems `num_systems - len(indices)`.
    """

    temp = array(state)

    for i, idx in enumerate(indices):
        offset = num_systems - i
        temp = temp.reshape((truncation+1,) * offset * 2)
        temp = trace(temp, axis1=(idx-i), axis2=(offset+idx-i))

    output_dim = (truncation + 1) ** (num_systems - len(indices))
    output_state = temp.reshape((output_dim, output_dim))
    return output_state


def random_state() -> list:
    """Generate a random pure state vector for a single qubit.
    
    The function returns a list of two elements representing the amplitudes of the quantum state
    in the computational basis [|0>, |1>]. The first element is a real number (float) corresponding
    to the amplitude of |0>, and the second element is a complex number corresponding to the amplitude of |1>.
    Returns:
        list: [float, complex] -- A list containing the amplitudes of the random qubit state.
    """
    u = random.random()
    θ = 2 * math.acos(math.sqrt(u))
    φ = 2 * math.pi * random.random()
    return [math.cos(θ / 2), complex(math.sin(θ / 2) * math.cos(φ), math.sin(θ / 2) * math.sin(φ))]


def verify_same_state_vector(state1: list, state2: list) -> bool:
    """Verify if two quantum state vectors are the same.
       Note that two state vectors are the same regardless of the global phase

    Args:
        state1 (list): The first quantum state vector.
        state2 (list): The second quantum state vector.
    
    Returns:
        bool: True if the state vectors are the same, False otherwise.
    """
    if len(state1) != len(state2):    # Length check
        return False

    global_phase = None               # Find the first non-zero element in state1/state2 to estimate the global phase
    for a, b in zip(state1, state2):
        if abs(a) > EPSILON and abs(b) > EPSILON:
            global_phase = b / a
            break

    if global_phase is None:
        return False

    global_phase /= abs(global_phase) # Normalize phase to have unit magnitude (global phase must be on the unit circle)

    for a, b in zip(state1, state2):  # Check if all elements match up to this global phase
        if abs(b - global_phase * a) > EPSILON:
            return False

    return True
