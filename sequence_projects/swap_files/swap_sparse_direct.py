from swap_TN_direct import *
from sequence.components.polarization_fock.quantum_manager import _build_amp_damping_kraus_operators

from numpy import kron
import scipy.sparse as sp

# a = qt.destroy(N).full()
# a = sp.csr_matrix(a)
# a_dag = a.T

# Support functions:
def create_op(left_indices, op, right_indices, N):
    if left_indices == 0:
        return sp.kron(op, sp.eye(N**right_indices))
    elif right_indices == 0:
        return sp.kron(sp.eye(N**left_indices), op)
    else:    
        out_op = sp.kron(sp.eye(N**left_indices), op)
        return sp.kron(out_op, sp.eye(N**right_indices))
def _find_mat_exp(mat):
    ans = sp.eye(mat.shape[0])
    intermediate = 1
    for i in range(1, 50+1):
        intermediate *= mat/i
        intermediate.eliminate_zeros()
        ans += intermediate
    return ans 
def read_quantum_state_sparse(sparse_state, N):
    temp_sparse_state = sp.csr_matrix(sparse_state)
    temp_sparse_state.data = np.round(temp_sparse_state.data, 10)
    temp_sparse_state.eliminate_zeros()
    labels = generate_labels(4,N)
    state = temp_sparse_state.nonzero()[0]
    print(f"{len(state)} non-zero elements Corresponding Basis terms:")
    for k in state: print(labels[k],"-",k,"-",temp_sparse_state[k].data)

def extend_state_sparse(state):
    return sp.kron(state, state)
# TMSV_state_dense = extend_state_sparse(TMSV_state)

def bell_state_measurement_sparse(TMSV_state_dense, N, efficiency, a_dag, use_kraus = False, is_dm = False):
    # BSM BS implementation
    BSM_H_0_Mode_op = create_op(2, a_dag, 5, N)
    BSM_V_0_Mode_op = create_op(3, a_dag, 4, N)
    BSM_H_1_Mode_op = create_op(6, a_dag, 1, N)
    BSM_V_1_Mode_op = create_op(7, a_dag, 0, N)

    hamiltonian_BS_H = -np.pi/4 * ( BSM_H_0_Mode_op.T@BSM_H_1_Mode_op - BSM_H_0_Mode_op@BSM_H_1_Mode_op.T )
    unitary_BS_H = _find_mat_exp(hamiltonian_BS_H)

    hamiltonian_BS_V = -np.pi/4 * ( BSM_V_0_Mode_op.T@BSM_V_1_Mode_op - BSM_V_0_Mode_op@BSM_V_1_Mode_op.T )
    unitary_BS_V = _find_mat_exp(hamiltonian_BS_V)


    # BSM povm implementation
    if not use_kraus:
        print("not using kraus")
        povm_op_1 = sp.csr_matrix(create_threshold_POVM_OP_Dense(efficiency, 1, N))
        povm_op_0 = sp.csr_matrix(create_threshold_POVM_OP_Dense(efficiency, 0, N))
    else:
        print("using kraus")
        povm_op_1 = sp.csr_matrix(create_threshold_POVM_OP_Dense(1, 1, N))
        povm_op_0 = sp.csr_matrix(create_threshold_POVM_OP_Dense(1, 0, N))

    BSM_povm = create_op(2, povm_op_1, 0, N)
    BSM_povm = create_op(0, sp.kron(BSM_povm, povm_op_0), 2, N)
    BSM_povm = sp.kron(BSM_povm, sp.kron(povm_op_0, povm_op_1))

    # print(unitary_BS_V.shape, unitary_BS_H.shape, TMSV_state_dense.shape)
    
    if is_dm:
        print(unitary_BS_V.shape)
        post_BS_State = unitary_BS_V @ unitary_BS_H @ TMSV_state_dense @ (unitary_BS_V @ unitary_BS_H).conj().T
        if use_kraus:
            print("using kraus")
            damping_kraus_ops = _build_amp_damping_kraus_operators(loss_rate = 1-efficiency, N = N)
            damping_kraus_ops_1 = [create_op(2, op, 4, N) for op in damping_kraus_ops]
            damping_kraus_ops_2 = [create_op(6, op, 0, N) for op in damping_kraus_ops]

            new_dm = 0
            for kraus_op in damping_kraus_ops_1:
                new_dm += kraus_op @ post_BS_State @ kraus_op.conj().T

            old_dm = new_dm
            post_BS_State = 0
            for kraus_op in damping_kraus_ops_2:
                post_BS_State += kraus_op @ old_dm @ kraus_op.conj().T

        post_BSM_State = BSM_povm @ post_BS_State @ BSM_povm.conj().T
    else:
        post_BS_State = unitary_BS_V @ unitary_BS_H @ TMSV_state_dense
        post_BSM_State = BSM_povm @ post_BS_State

    # post_BSM_State.data = np.round(post_BSM_State.data, 10)
    # post_BSM_State.eliminate_zeros()

    return post_BSM_State
# post_BSM_State = bell_state_measurement_sparse(TMSV_state_dense, N, efficiency)

def rotate_and_measure_sparse(post_BSM_State, N, efficiency, a_dag):
    # Polarization rotators mode operators
    rotator_H_0_Mode_op = create_op(0, a_dag, 7, N)
    rotator_V_0_Mode_op = create_op(1, a_dag, 6, N)
    rotator_H_1_Mode_op = create_op(4, a_dag, 3, N)
    rotator_V_1_Mode_op = create_op(5, a_dag, 2, N)

    povm_op_1 = sp.csr_matrix(create_threshold_POVM_OP_Dense(efficiency, 1, N))

    # polarization analysis detector POVMs
    pol_analyzer_povm = create_op(0, povm_op_1, 3, N)
    pol_analyzer_povm = create_op(0, sp.kron(pol_analyzer_povm, povm_op_1), 3, N)

    # Applying rotations and measuring

    signal_angles = [0, np.pi/2] # np.linspace(0, np.pi, 20)
    # idler_angles = np.linspace(0, np.pi, 20)
    idler_angles = [0] # np.linspace(0, np.pi, 20)
    coincidence = []

    for i, idler_angle in enumerate(idler_angles):
        coincidence_probs = []

        hamiltonian_rotator_1 = -idler_angle * ( rotator_H_1_Mode_op.T@rotator_V_1_Mode_op - rotator_H_1_Mode_op@rotator_V_1_Mode_op.T )
        unitary_rotator_1 = _find_mat_exp(hamiltonian_rotator_1)
        post_idler_detection_state = unitary_rotator_1 @ post_BSM_State
        # post_idler_detection_state = post_BSM_State
        
        for j, angle in enumerate(signal_angles):
            # print("idler:", i, "signal:", j)
        
            hamiltonian_rotator_0 = -angle * ( rotator_H_0_Mode_op.T@rotator_V_0_Mode_op - rotator_H_0_Mode_op@rotator_V_0_Mode_op.T )
            unitary_rotator_0 = _find_mat_exp(hamiltonian_rotator_0)
            post_rotations_state = unitary_rotator_0 @ post_idler_detection_state

            measured_state = pol_analyzer_povm @ post_rotations_state

            coincidence_probs.append(sp.linalg.norm(measured_state)**2)
        coincidence.append(coincidence_probs)
    return coincidence, idler_angles
# coincidence, idler_angles = rotate_and_measure_sparse(post_BSM_State, N, efficiency)