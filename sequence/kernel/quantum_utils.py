"""This module defines functions and objects to manipulate quantum states.

This includes cached measurement of quantum states, and certain useful operators.
These should not be used directly, but accessed by a QuantumManager instance or by a quantum state.
"""

from functools import lru_cache
from typing import List, Tuple
from math import sqrt

from numpy import array, kron, identity, zeros, trace, outer, eye
from scipy.linalg import sqrtm

from scipy import sparse as sp
create_spare_matrix = lambda data, basis_dim, num_systems: sp.csr_matrix(data, (basis_dim**num_systems, basis_dim**num_systems))


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
def measure_entangled_state_with_cache(state: Tuple[complex], basis: Tuple[Tuple[complex]], state_index: int,
                                       num_states: int) -> \
        Tuple[array, array, float]:

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
        -> Tuple[List[array], List[float]]:

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
def measure_state_with_cache_ket(state: Tuple[complex, complex]) -> float:

    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = (state.conj().T @ M0 @ state).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_ket(state: Tuple[complex], state_index: int, num_states: int) \
        -> Tuple[array, array, float]:

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
def measure_multiple_with_cache_ket(state: Tuple[complex], num_states: int, length_diff: int) \
        -> Tuple[List[array], List[float]]:

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
def measure_state_with_cache_density(state: Tuple[Tuple[complex, complex]]) -> float:

    state = array(state)
    M0 = array([[1, 0], [0, 0]], dtype=complex)

    # probability of measuring basis[0]
    prob_0 = trace(state @ M0).real
    return prob_0


@lru_cache(maxsize=1000)
def measure_entangled_state_with_cache_density(state: Tuple[Tuple[complex]], state_index: int, num_states: int) \
        -> Tuple[array, array, float]:

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
def measure_multiple_with_cache_density(state: Tuple[Tuple[complex]], num_states: int, length_diff: int) \
        -> Tuple[List[array], List[float]]:

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
def measure_state_with_cache_fock_density(state: Tuple[Tuple[complex]], povms: Tuple[Tuple[Tuple[complex]]]) \
        -> Tuple[List[array], List[float]]:
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
def measure_entangled_state_with_cache_fock_density(state: Tuple[Tuple[complex]], system_index: int, num_systems: int,
                                                    povms: Tuple[Tuple[Tuple[complex]]], truncation: int = 1) \
        -> Tuple[List[array], List[float]]:

    """Measure one subsystem of a larger composite system.

    The measurement SHOULD NOT be entangling measurement, and thus POVM operators should be precisely consisted of
    operators on the subsystem's Hilbert space alone.

    Args:
        state (Tuple[Tuple[complex]]): state to measure
        system_index (int): index of measured subsystem within state.
        num_systems (int): number of total systems in the state.
        povms (Tuple[Tuple[Tuple[complex]]]): tuple listing all POVM operators to use for measurement
        truncation (int): fock space truncation, 1 for qubit system (default 1).

    Returns:
        Tuple[List[array], List[float]]: tuple with two sub-lists.
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
def measure_multiple_with_cache_fock_density(state: Tuple[Tuple[complex]], indices: Tuple[int], num_systems: int,
                                             povms: Tuple[Tuple[Tuple[complex]]], truncation: int = 1) \
        -> Tuple[List[array], List[float]]:

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
        state (Tuple[Tuple[complex]]): state to measure.
        indices (Tuple[int]): indices within combined state to measure.
        num_systems (int): number of total systems in the state.
        povms (Tuple[Tuple[Tuple[complex]]]): tuple listing all POVM operators to use for measurement.
        truncation (int): fock space truncation, 1 for qubit system (default 1).

    Returns:
        Tuple[List[array], List[float]]: tuple with two sub-lists.
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
def density_partial_trace(state: Tuple[Tuple[complex]], indices: Tuple[int], num_systems: int, truncation: int = 1) \
        -> array:

    """Traces out subsystems systems at given indices.

    Args:
        state (Tuple[Tuple[complex]]: input state.
        indices (Tuple[int]): indices of subsystems to trace out of state.
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


@lru_cache(maxsize=1000)
def sparse_measure_state_with_cache_fock_density(state: Tuple[Tuple[complex]], povms: Tuple[Tuple[Tuple[complex]]], sqrt_povms, basis_dim: int) \
        -> Tuple[List[array], List[float]]:
    
    """
    This function simply takes a single input state and measures it. Its a convenience function and could be done by the multiple/entangled 
    methods as well. This is simply for better perfromance in the simpler case. 

    Now, based on the previous implementations, we could use the square roots of the POVM operator as the measurement operators. This however,
    is not a standard practice. POVM ops are generally used when the entire quantum circuit has been executed and the final step of the circuit 
    is measurement and we do not care about the post measurement state anyways. This also what is done in most analytical descriptions.

    Hence, to maintain backward compatibility, I provide the option to use the sqrt povms case, but I will generally use it to make the 
    implementation easier to understand and relate with theory. 

    So, in the regular case, we simply take in the POVM ops (which could be anything- regular POVMs for probability estimation or squares of POVMs
    for variance estimation). Only restriction here is that there is a maximum of one system being measured in the total system which is also the 
    very system being measured alone. 

    Args:
        state: the state being measured (this should be (basis_dim,basis_dim) in dimension) (check this)
        povms: the povms used to measure the state. Again, (basis_dim,basis_dim) in dimension (check this)
        sqrt_povms: Square root of the povms. Preferably set this to None and use regular measurments.
        basis_dim: The dimensionality of the hilbert space where the quantum systems live. 


    """
    state = create_spare_matrix(state, basis_dim, 1)
    povms = [create_spare_matrix(povm, basis_dim, 1) for povm in povms]

    # probabilities of getting different outcomes according to POVM operators
    prob_list = [(state @ povm).trace().real for povm in povms]
    state_list = []

    # All of this code is if the sqrt is not None and we are interested in the post-measurement state.
    if not sqrt_povms == None:
        sqrt_povms = [create_spare_matrix(povm, basis_dim, 1) for povm in sqrt_povms]
        for i in range(len(prob_list)):
            if prob_list[i] <= 0:
                state_post_meas = None
            else:
                measure_op = sqrt_povms[i]
                state_post_meas = (measure_op @ state @ measure_op) / prob_list[i]

            state_list.append(state_post_meas)
        
        return state_list, prob_list

    return None, prob_list


@lru_cache(maxsize=1000)
def sparse_measure_entangled_state_with_cache_fock_density(state: Tuple[Tuple[complex]], key_index: int, len_all_keys: int,
                                                    povms: Tuple[Tuple[Tuple[complex]]], sqrt_povms=None, basis_dim: int = 4):

    """
    This is also a convenience function where unlike in '''sparse_measure_state_with_cache_fock_density''', the overall state could have 
    multiple systems of which we are measuring just one subsystem. See the docstring for '''sparse_measure_state_with_cache_fock_density''' 
    for a discussion on sqrt_povms which also applies here. 

    Args:
        state (Tuple[Tuple[complex]]): state to measure
        key_index (int): index of measured subsystem within state.
        len_all_keys (int): number of total systems in the state.
        povms (Tuple[Tuple[Tuple[complex]]]): tuple listing all POVM operators to use for measurement
        sqrt_povms: Square root of the povms. Preferably set this to None and use regular measurments.
        basis_dim: The dimensionality of the hilbert space where the quantum systems live. 

    """


    state = create_spare_matrix(state, basis_dim, len_all_keys) # The overall state has len_all_keys number of sub-systems. You measure just one of them. 
    povms = [create_spare_matrix(povm, basis_dim, 1) for povm in povms] # You put 1 there since you are measuring just one state

    # ###### BASICALLY THE _prepare_operator_method FROM THE QUANTUM MANAGER ###############
    # # generate POVM operators on total Hilbert space.
    povm_list = []
    sqrt_povm_list = []
    left_dim = basis_dim ** key_index
    right_dim = basis_dim ** (len_all_keys - key_index - 1)
    # print(basis_dim ** len_all_keys, "left_dim", left_dim, "right_dim", right_dim, "povms[0].shape", povms[0].shape)
    for i in range(len(povms)):
        povm_list.append( sp.kron(sp.kron(sp.eye(left_dim), povms[i]), sp.eye(right_dim)) )
        # sqrt_povm_list.append( sp.kron(sp.kron(sp.eye(left_dim), sqrt_povms[i]), sp.eye(right_dim)) )
    ########################################################################################

    # (prob = Tr(ρ.M)) list of probabilities of getting different outcomes from POVM.
    # print("state.shape", state.shape, "povm.shape", povm_list[0].shape)
    prob_list = [(state @ povm).trace().real for povm in povm_list]
    state_list = []

    if not sqrt_povms == None:
        sqrt_povms = [create_spare_matrix(povm, basis_dim, 1) for povm in sqrt_povms]

        for i in range(len(povms)):
            sqrt_povm_list.append( sp.kron(sp.kron(sp.eye(left_dim), sqrt_povms[i]), sp.eye(right_dim)) )

        for i in range(len(prob_list)):
            if prob_list[i] <= 0:
                state_post_meas = None
            else:
                measure_op = sqrt_povm_list[i]
                state_post_meas = (measure_op @ state @ measure_op) / prob_list[i]

            state_list.append(state_post_meas)
    else:
        return None, prob_list

    return state_list, prob_list



@lru_cache(maxsize=1000)
def sparse_measure_multiple_with_cache_fock_density(state: Tuple[Tuple[complex]], key_indices: Tuple[int], len_all_keys: int,
                                             povms: Tuple[Tuple[Tuple[complex]]], basis_dim: int) \
        -> Tuple[List[array], List[float]]:

    """Measure multiple subsystems of a larger composite system.

    Args:
        state (Tuple[Tuple[complex]]): state to measure.
        indices (Tuple[int]): indices within combined state to measure.
        num_systems (int): number of total systems in the state.
        povms (Tuple[Tuple[Tuple[complex]]]): tuple listing all POVM operators to use for measurement.
        truncation (int): fock space truncation, 1 for qubit system (default 1).

    Returns:
        Tuple[List[array], List[float]]: tuple with two sub-lists.
            The first lists each output state, corresponding with the measurement of each POVM.
            The second lists the probability for each measurement.
    """

    state = create_spare_matrix(state, basis_dim, len_all_keys)
    povms = [create_spare_matrix(povm, basis_dim, len(key_indices)) for povm in povms]

    # judge if elements in `indices` are consecutive
    init_meas_sys_idx = min(key_indices)
    fin_meas_sys_idx = max(key_indices)
    num = len(key_indices)
    if (fin_meas_sys_idx - init_meas_sys_idx + 1 != num) or (list(key_indices) != sorted(key_indices)):
        raise ValueError("Indices should be consecutive; got {}".format(key_indices))

    povm_list = []
    left_dim = basis_dim ** init_meas_sys_idx
    right_dim = basis_dim ** (len_all_keys - fin_meas_sys_idx - 1)
    for povm in povms:
        povm_tot = sp.kron(sp.kron(sp.eye(left_dim), povm), sp.eye(right_dim))
        povm_list.append(povm_tot)

    # list of probabilities of getting different outcomes from POVM
    prob_list = [(state @ povm).trace().real for povm in povm_list]


    return None, prob_list




@lru_cache(maxsize=1000)
def sparse_density_partial_trace(state: Tuple[Tuple[complex]], key_indices: Tuple[int], len_all_keys: int, basis_dim: int):

    temp = create_spare_matrix(state, basis_dim, len_all_keys)

    len_keys = len(key_indices)
    len_left_indices = key_indices[0]
    len_right_indices = len_all_keys-key_indices[-1]-1
    
    left_op = sp.eye(basis_dim**len_left_indices, format = "csr")
    basis = sp.eye(basis_dim**len_keys, format = "csc")
    right_op = sp.eye(basis_dim**len_right_indices, format = "csr")

    output_state = 0
    for i in range(basis_dim**len_keys):
        op = sp.kron(left_op, basis[:,i])
        op = sp.kron(op, right_op)
        output_state += op.transpose() @ temp @ op
    return sp.csr_matrix(output_state)