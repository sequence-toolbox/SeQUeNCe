# import qutip as qtp
from qutip import basis, identity, sigmax, sigmaz, tensor, bell_state
from qutip.measurement import measure_povm
from qutip_qip.operations import hadamard_transform, cnot, swap
import numpy as np
from sequence.resource_management.memory_manager import MemoryManager 

import qutip as qt
from itertools import combinations
from typing import List
import math

def _filter_basis_pairs(pairs: List, num_qubits: int):
    '''Helper function. Filters the list of basis vectors such that for each pair their binary
    representations are different at each qubit index.
    
    Args: 
        pairs: list of pairs of integers. The integers denote vectors in the standard basis
        for the specified number of qubits.
        num_qubits: number of qubits.'''
    new_pairs=[]
    for p in pairs:
        int_p0=p[0]
        int_p1=p[1]
        p0=bin(int_p0)[2:].zfill(num_qubits)
        p1=bin(int_p1)[2:].zfill(num_qubits)
        if all([p0[idx]!=p1[idx] for idx in range(num_qubits)]):
            new_pairs.append([int_p0, int_p1])        
    return new_pairs


def calc_scalar_c(rho: qt.Qobj, tol=1e-09):
    """Calculates the scalar C.

    C=2*sum_(a,b)[l_a*l_b/(l_a+l_b)], l_a and l_b
    are the l_i=<i|rho|i>, where |i> is the generalized Bell basis. The input state
    is diagonal in the generalized Bell basis so we take the eigenvalue decomposition of rho.
    l_a and l_b are paired based on oposite relative phase: |a>=|s_1>+|s_2> and |b>=|s_1>-|s_2>,
    where |s_i> is an element of the standard basis.
    
    Args:
        rho: density matrix
        tol: numerical tolerance
    
    Return
        C: float
    """

    qobj_dim = rho.dims[0]
    vec_dim = np.prod(qobj_dim)
    std_basis_vecs = list(range(vec_dim))  # integer rep of standard basis elements.
    std_basis_pairs = list(combinations(std_basis_vecs, 2))
    # the filter ensures that each pair of strings have different values at each index.
    # this ensures that equal superpositions of are bipartite maximally entangled.
    std_basis_pairs = _filter_basis_pairs(std_basis_pairs, int(math.log2(vec_dim)))
    c_val = 0

    for idx1, idx2 in std_basis_pairs:
        # construct matrix representations of basis vectors.
        vec1 = [[0]*vec_dim]
        vec1[0][idx1] = 1
        vec1 = qt.Qobj(vec1, dims=[[1], qobj_dim])

        vec2 = [[0]*vec_dim]
        vec2[0][idx2] = 1
        vec2 = qt.Qobj(vec2, dims=[[1], qobj_dim])

        # eigenvalues
        vec_plus = (vec1+vec2).unit()
        vec_minus = (vec1-vec2).unit()
        val1 = (vec_plus * rho * vec_plus.trans().conj())
        val2 = (vec_minus * rho * vec_minus.trans().conj())
        if abs(val1+val2) > tol:
            c_val += (val1*val2)/(val1+val2)

    return 4 * c_val  # multiplying by 4 since the order of the eigenvalues in the sum matters.


def calculate_fidelity(state):
    """Calculates fidelity of input GHZ state."""
    ghz_dim = state.dims[0]
    desired_ghz_arr = np.zeros(np.prod(ghz_dim))
    desired_ghz_arr[0] = np.sqrt(1/2)
    desired_ghz_arr[-1] = np.sqrt(1/2)
    desired_ghz = qt.Qobj(desired_ghz_arr, dims=[ghz_dim, [1]])

    fidelity = np.abs(desired_ghz.dag() * state * desired_ghz)
    return fidelity


def purification_result(state1, state2, gate_fid1, gate_fid2, meas_fid1, meas_fid2, is_twirled=True):
    """Function to derive purification success probability and output state.

    Codes are modified from SeQUeNCe purification.py.
    Variable name correspondence between current implementation and SeQUeNCe:
        gate_fid1 <--> own_node_gate_fid
        gate_fid2 <--> remote_node_gate_fid
        meas_fid1 <--> own_node_meas_fid
        meas_fid2 <--> remote_node_meas_fid
    
    Return:
        p_succ (float): success probability
        bds_elems (List): list of successful output BDS diagonal elements
    """

    if is_twirled:
        kept_elem_1, kept_elem_2, kept_elem_3, kept_elem_4 = state1[0], (1-state1[0])/3, (1-state1[0])/3, (1-state1[0])/3  # Diagonal elements of kept pair (twirled)
        meas_elem_1, meas_elem_2, meas_elem_3, meas_elem_4 = state2[0], (1-state2[0])/3, (1-state2[0])/3, (1-state2[0])/3  # Diagonal elements of measured pair (twirled)   
    else:
        kept_elem_1, kept_elem_2, kept_elem_3, kept_elem_4 = state1  # Diagonal elements of kept pair
        meas_elem_1, meas_elem_2, meas_elem_3, meas_elem_4 = state2  # Diagonal elements of measured pair

    assert 1. >= kept_elem_1 >= 0.5 and 1. >= meas_elem_1 >= 0.5, "Input states should have fidelity above 1/2."
    a, b = (kept_elem_1 + kept_elem_2), (meas_elem_1 + meas_elem_2)

    # calculate success probability with analytical formula
    p_succ = gate_fid1 * gate_fid2 * (meas_fid1 * (1-meas_fid2) + (1-meas_fid1) * meas_fid2) \
            + gate_fid1 * gate_fid2 * (a*b + (1-a)*(1-b)) \
                * (meas_fid1 * meas_fid2 + (1-meas_fid1)*(1-meas_fid2) - meas_fid1 * (1-meas_fid2) - (1-meas_fid1) * meas_fid2) \
            - gate_fid1 * gate_fid2 / 2 + 1/2

    new_elem_1 = gate_fid1 * gate_fid2 \
        * ((meas_fid1 * meas_fid2 + (1-meas_fid1)*(1-meas_fid2))*(kept_elem_1*meas_elem_1 + kept_elem_2*meas_elem_2)
            + (meas_fid1 * (1-meas_fid2) + (1-meas_fid1) * meas_fid2)*(kept_elem_1*meas_elem_3 + kept_elem_2*meas_elem_4)) \
        + (1 - gate_fid1 * gate_fid2) / 8

    new_elem_2 = gate_fid1 * gate_fid2 \
        * ((meas_fid1 * meas_fid2 + (1-meas_fid1)*(1-meas_fid2))*(kept_elem_1*meas_elem_2 + kept_elem_2*meas_elem_1)
            + (meas_fid1 * (1-meas_fid2) + (1-meas_fid1) * meas_fid2)*(kept_elem_1*meas_elem_4 + kept_elem_2*meas_elem_3))\
        + (1 - gate_fid1 * gate_fid2) / 8

    new_elem_3 = gate_fid1 * gate_fid2 \
        * ((meas_fid1 * meas_fid2 + (1-meas_fid1)*(1-meas_fid2))*(kept_elem_3*meas_elem_3 + kept_elem_4*meas_elem_4)
            + (meas_fid1 * (1-meas_fid2) + (1-meas_fid1) * meas_fid2)*(kept_elem_3*meas_elem_1 + kept_elem_4*meas_elem_2)) \
        + (1 - gate_fid1 * gate_fid2) / 8

    new_elem_4 = gate_fid1 * gate_fid2 \
        * ((meas_fid1 * meas_fid2 + (1-meas_fid1)*(1-meas_fid2))*(kept_elem_3*meas_elem_4 + kept_elem_4*meas_elem_3)
            + (meas_fid1 * (1-meas_fid2) + (1-meas_fid1) * meas_fid2)*(kept_elem_3*meas_elem_2 + kept_elem_4*meas_elem_1))\
        + (1 - gate_fid1 * gate_fid2) / 8

    if is_twirled:
        new_fid = new_elem_1 / p_succ  # normalization by success probability
        bds_elems = [new_fid, (1-new_fid)/3, (1-new_fid)/3, (1-new_fid)/3]
    else:
        new_elems = [new_elem_1, new_elem_2, new_elem_3, new_elem_4]
        bds_elems = [elem / p_succ for elem in new_elems]  # normalization by success probability
    
    return p_succ, bds_elems


# Final purification
def final_purification(bds_list, gate_fid1, gate_fid2, meas_fid1, meas_fid2, is_twirled=True):
    """Function to perform the final purification of EPR pairs between node 1 (own node in SeQUeNCe) and node 2 (remote node in SeQUeNCe),
        to make sure that the link has at most one EPR pair left.
    
    Special consideration:
        When input states are non-identical, especially with large difference, 
        the successful output state's fidelity might not be higher than the higher fidelity among the two input states.

    Heuristic strategy (pumping):
        Each round find two EPR pairs from the remaining EPR pairs with lowest fidelity and purify them, and remove them from the list:
            if successful, append the successful output state to the list of remaining EPR pairs,
            if unsuccessful, do nothing,
        Repeat the first step until there is at most one EPR pair in the list.

    Args:
        bds_list (List[array]): list of remaining BDS diagonal element arrays
        gate_fid1 (float): gate fidelity on node 1
        gate_fid2 (float): gate fidelity on node 2
        meas_fid1 (float): measurement fidelity on node 1
        meas_fid2 (float): measurement fidelity on node 2
        is_twirled (bool): if twirling is applied to keep the input and output in Werner form

    Return:
        bds_remain (array): diagonal element array of the final remaining BDS, might be empty if final purification failed
    """

    # sort the list of BDS diagonal element arrays in fidelity ascending order
    bds_list.sort(key=(lambda x: x[0]))

    while len(bds_list) > 1:
        state1 = bds_list[0]
        state2 = bds_list[1]

        bds_list = bds_list[2:]

        p_succ, bds_elems = purification_result(state1, state2, gate_fid1, gate_fid2, meas_fid1, meas_fid2, is_twirled)

        if np.random.uniform() < p_succ:
            bds_list.append(bds_elems)
        
        bds_list.sort(key=(lambda x: x[0]))

    if len(bds_list) == 1:
        return bds_list[0]
    elif len(bds_list) == 0:
        return bds_list


# Ad hoc generation of 3-qubit GHZ state from 2 BDS
# we assume all 1-qubit gates are perfect, only 1-qubit measurements and multi-qubit gates are noisy
# before performing GHZ generation, BDS from SeQUeNCe simulation must check their memories' last_update_time, to make sure that all idling decoherence is included

def bell_dm(state, elem_order=(0, 1, 2, 3)):
    """Function to create BDS density matrix as QuTiP Qobj instance.

    4 Bell states: Phi+ (|00>+|11>), Phi- (|00>-|11>), Psi+ (|01>+|10>), Psi- (|01>-|10>) are ordered as 0,1,2,3.
    Will use bell_state() function inside QuTiP.
    
    Args:
        state (np.ndarray): 1-d array of 4 BDS density matrix diagonal elements.
        elem_order (List[int]): the indices of corresponding Bell states for the 4 BDS density matrix diagonal elements.

    Return:
        bell_dm (Qobj): BDS density matrix as QuTiP Qobj.
    """

    bell_dm = 0  # initialization

    for elem, idx in zip(state, elem_order):
        idx_str = format(idx, '02b')  # transform Bell state index into binary strings for bell_state() function in QuTiP
        pure_bell_dm = bell_state(idx_str) * bell_state(idx_str).dag()
        bell_dm += elem * pure_bell_dm

    return bell_dm


def noisy_meas(fid):
    """Function to create a 2-element POVM correponding to a noisy 1-qubit measurement.

    Modeled as a mixture of correct and incorrect projectors.

    Arg:
        fid (float): fidelity of the noisy measurement, equal to the probability of correct projector in the mixture.
    
    Return:
        noisy_meas (List[Qobj]): measurement operators, which are square root of the POVMs
    """

    meas_0 = (np.sqrt(fid) * basis(2,0) * basis(2,0).dag() +
              np.sqrt(1-fid) * basis(2,1) * basis(2,1).dag())
    meas_1 = (np.sqrt(fid) * basis(2,1) * basis(2,1).dag() +
              np.sqrt(1-fid) * basis(2,0) * basis(2,0).dag())

    return [meas_0, meas_1]


def merge(state1, state2, cnot_fid, meas_fid):
    """Ad hoc function to generate a 3-qubit GHZ state from 2 BDS using imperfect GHZ merging, 
        where noisy CNOT is modeled as a mixture of noiseless CNOT and 2-qubit completely depolarizing channel.

    Input states should be QuTiP quantum objects (density matrix). 
    BDS should have major component as (|00> + |11>)/sqrt{2}.

    Args:
        state1 (Qobj): first BDS density matrix.
        state2 (Qobj): second BDS density matrix.
        cnot_fid (float): fidelity of noisy CNOT gate.
        meas_fid (float): fidelity of noisy 1-qubit measurement.
    
    Return
        ghz_state (Qobj): generated GHZ state.
    """

    bell_dm_1 = bell_dm(state1)
    bell_dm_2 = bell_dm(state2)
    init_state = tensor(bell_dm_1, bell_dm_2)  # initial state as tensor product of two BDS, qubits are labeled 0,1,2,3

    # apply CNOT between two BDS, control on qubit 1 and target on qubit 2
    cnot_12 = tensor(identity(2), cnot(), identity(2))  # noiseless CNOT unitary
    swap_12 = tensor(identity(2), swap(), identity(2))
    swap_23 = tensor(identity([2, 2]), swap())
    post_cnot_state = cnot_fid * cnot_12 * init_state * cnot_12.dag()\
          + (1-cnot_fid) * swap_23 * swap_12 * (tensor(init_state.ptrace([0, 3]), identity([2, 2]))/4) * swap_12.dag() * swap_23.dag()

    # apply noisy measurement on qubit 2
    meas0, meas1 = noisy_meas(meas_fid)  # 1-qubit measurement operators
    meas0 = tensor(identity([2, 2]), meas0, identity(2))
    meas1 = tensor(identity([2, 2]), meas1, identity(2))
    meas_ops = [meas0, meas1]
    res, post_meas_state = measure_povm(post_cnot_state, meas_ops)

    # trace out qubit 2
    post_meas_state = post_meas_state.ptrace([0, 1, 3])

    # apply feedforward X correction on qubit 0 if measure result is 1 (now remaining qubit 0, 1, 2)
    if res == 0:
        ghz_state = post_meas_state
    if res == 1:
        x_gate = tensor(sigmax(), identity([2, 2]))
        ghz_state = x_gate * post_meas_state * x_gate.dag()

    return ghz_state


def gate_teleport(state1, state2, cnot_fid, meas_fid):
    """Ad hoc function to generate a 3-qubit GHZ state from 2 BDS using imperfect CNOT teleportation, 
        where noisy CNOT is modeled as a mixture of noiseless CNOT and 2-qubit completely depolarizing channel.

    Input states should be QuTiP quantum objects (density matrix). 
    BDS should have major component as (|01> + |10>)/sqrt{2}.
    Following derivation in (Chou, Kevin S., et al. "Deterministic teleportation of a quantum gate between two logical qubits." Nature 561.7723 (2018): 368-373.)
    We assume center qubit (control) is initialized in |+> state, and other two qubits (targets) are initialized in |0> state.

    Args:
        state1 (Qobj): first BDS density matrix.
        state2 (Qobj): second BDS density matrix.
        cnot_fid (float): fidelity of noisy CNOT gate.
        meas_fid (float): fidelity of noisy 1-qubit measurement.
    
    Return
        ghz_state (Qobj): generated GHZ state.
    """

    bell_dm_1 = bell_dm(state1)
    bell_dm_2 = bell_dm(state2)

    meas0, meas1 = noisy_meas(meas_fid)  # 1-qubit measurement operators

    plus_state = (basis(2,0) + basis(2,1)) / np.sqrt(2)
    plus_dm = plus_state * plus_state.dag()
    zero_dm = basis(2,0) * basis(2,0).dag()

    ### 1st teleported CNOT
    init_state = tensor(plus_dm, bell_dm_1, zero_dm)

    cnot_01 = tensor(cnot(), identity(4))
    cnot_23 = tensor(identity(4), cnot())
    cnot_01_23 = cnot_01 * cnot_23

    state_both_succ = cnot_01_23 * init_state * cnot_01_23.dag()
    state_01_succ = tensor((cnot_01 * init_state * cnot_01.dag()).ptrace([0,1]), identity(4)/4)
    state_23_succ = tensor(identity(4)/4, (cnot_23 * init_state * cnot_23.dag()).ptrace([2,3]))
    state_both_fail = tensor(identity(4)/4, identity(4)/4)

    post_cnot_state = cnot_fid**2 * state_both_succ + cnot_fid * (state_01_succ + state_23_succ) + (1-cnot_fid)**2 * state_both_fail

    # measure qubit 1 in Z basis
    # full measurement operators for qubit 1 (measure in Z basis)
    meas0_1 = tensor(identity(2), meas0, identity(4))
    meas1_1 = tensor(identity(2), meas1, identity(4))
    meas_ops_1 = [meas0_1, meas1_1]

    res1, post_meas1_state = measure_povm(post_cnot_state, meas_ops_1)

    # measure qubit 2 in X basis
    # full measurement operators for qubit 2 (measure in X basis, thus need Hadamard gate prior to meas)
    meas0_2 = tensor(identity(4), meas0, identity(2))
    meas1_2 = tensor(identity(4), meas1, identity(2))
    meas_ops_2 = [meas0_2, meas1_2]

    hadamard_2 = tensor(identity(4), hadamard_transform(), identity(2))
    post_meas1_state = hadamard_2 * post_meas1_state * hadamard_2.dag()

    res2, post_meas2_state = measure_povm(post_meas1_state, meas_ops_2)

    # trace out qubits 1 and 2
    post_meas_state = post_meas2_state.ptrace([0,3])
    # apply feedforward Z correction on qubit 0 if qubit 2 measurement result is 1
    # apply feedforward X correction on qubit 3 if qubit 1 measurement result is 1
    x_gate = tensor(identity(2), sigmax())
    z_gate = tensor(sigmaz(), identity(2))
    if res1 == 0 and res2 == 0:
        final_state = post_meas_state
    elif res1 == 1 and res2 == 0:
        final_state = x_gate * post_meas_state * x_gate.dag()
    elif res1 == 0 and res2 == 1:
        final_state = z_gate * post_meas_state * z_gate.dag()
    elif res1 == 1 and res2 == 1:
        final_state = z_gate * x_gate * post_meas_state * x_gate.dag() * z_gate.dag()
    
    ### 2nd teleported CNOT
    # previously the center qubit is indexed 0
    # now we swap it to qubit 1, so that it can be a direct neighbor of the second BDS, and serve as the control again
    final_state = swap() * final_state * swap().dag()
    init_state = tensor(final_state, bell_dm_2, zero_dm)

    cnot_12 = tensor(identity(2), cnot(), identity(4))
    cnot_34 = tensor(identity(8), cnot())
    cnot_12_34 = cnot_12 * cnot_34

    state_both_succ = cnot_12_34 * init_state * cnot_12_34.dag()
    state_12_succ = tensor((cnot_12 * init_state * cnot_12.dag()).ptrace([0,1,2]), identity(4)/4)
    state_34_succ = tensor(identity(4)/4, (cnot_34 * init_state * cnot_34.dag()).ptrace([0,3,4]))
    # swap current qubits 0, 1, 2 to 1, 2, 0 (first 1 <-> 2, then 0 <-> 1)
    swap_01 = tensor(swap(), identity(8))
    swap_12 = tensor(identity(2), swap(), identity(2))
    state_34_succ = swap_01 * swap_12 * state_34_succ * swap_12.dag() * swap_01.dag()
    state_both_fail = tensor(init_state.ptrace([0]), identity(4)/4, identity(4)/4)

    post_cnot_state = cnot_fid**2 * state_both_succ + cnot_fid * (state_12_succ + state_34_succ) + (1-cnot_fid)**2 * state_both_fail

    # measure qubit 2 in Z basis
    # full measurement operators for qubit 2 (measure in Z basis)
    meas0_2 = tensor(identity(4), meas0, identity(4))
    meas1_2 = tensor(identity(4), meas1, identity(4))
    meas_ops_2 = [meas0_2, meas1_2]

    res2, post_meas2_state = measure_povm(post_cnot_state, meas_ops_2)

    # measure qubit 3 in X basis
    # full measurement operators for qubit 3 (measure in X basis, thus need Hadamard gate prior to meas)
    meas0_3 = tensor(identity(4), meas0, identity(2))
    meas1_3 = tensor(identity(4), meas1, identity(2))
    meas_ops_3 = [meas0_3, meas1_3]

    hadamard_3 = tensor(identity(8), hadamard_transform(), identity(2))
    post_meas1_state = hadamard_3 * post_meas2_state * hadamard_3.dag()

    res3, post_meas2_state = measure_povm(post_meas2_state, meas_ops_3)

    # trace out qubits 2 and 3
    post_meas_state = post_meas2_state.ptrace([0,1,4])
    # apply feedforward Z correction on qubit 1 if qubit 3 measurement result is 1
    # apply feedforward X correction on qubit 4 if qubit 2 measurement result is 1
    x_gate = tensor(identity(4), sigmax())
    z_gate = tensor(identity(2), sigmaz(), identity(2))
    if res2 == 0 and res3 == 0:
        ghz_state = post_meas_state
    elif res2 == 1 and res3 == 0:
        ghz_state = x_gate * post_meas_state * x_gate.dag()
    elif res2 == 0 and res3 == 1:
        ghz_state = z_gate * post_meas_state * z_gate.dag()
    elif res2 == 1 and res3 == 1:
        ghz_state = z_gate * x_gate * post_meas_state * x_gate.dag() * z_gate.dag()

    return ghz_state

