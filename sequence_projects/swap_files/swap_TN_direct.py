# from src.components.polarizationFock.light_source import SPDCSource
# from src.kernel.timeline import Timeline
# from src.components.photon import Photon
# from src.kernel.quantum_manager import POLARIZATION_FOCK_FORMALISM
# from src.utils.encoding import polarizationFock
from scipy import sparse as sp

from sequence.components.polarization_fock import light_source as seq_ls
from sequence.kernel.timeline import Timeline 
from sequence.kernel.quantum_manager import POLARIZATION_FOCK_FORMALISM

# import tensornetwork as tn
import numpy as np
from numpy.linalg import matrix_power
import qutip as qt
from numpy import kron, sqrt
from scipy import sparse as sp 
from scipy.linalg import expm, sqrtm
from math import factorial
from matplotlib import pyplot as plt
# plt.style.use('dark_background')
import re


# %config InlineBackend.figure_formats = ['svg']
from quimb.tensor import MatrixProductState as mps #type: ignore
from quimb.tensor import MatrixProductOperator as mpo #type: ignore
from quimb.tensor.tensor_arbgeom import tensor_network_apply_op_vec #type: ignore
from quimb.tensor.tensor_core import new_bond #type: ignore
from quimb.tensor.tensor_1d_compress import enforce_1d_like #type: ignore
from quimb.tensor.tensor_1d import TensorNetwork1DOperator #type: ignore

from functools import lru_cache


###### SUPPORT FUNCTIONS ######

# Vacuum state creation
def fill_fn(shape):
    arr = np.zeros(shape)
    idx = tuple([0]*(len(shape)))
    arr[idx] = 1
    return arr
def create_vacuum_state(num_modes, N, bond_dim = 2):
    return mps.from_fill_fn(
                fill_fn,
                L=num_modes,
                bond_dim=bond_dim,
                phys_dim=N,
                cyclic=False,
                tags="In"
            )

# Generating labels for reading state. 
def generate_labels(num_systems, N):
    dim = N**2
    labels = []
    state_labels = []
    for i in range(dim):
        state_labels.append(f"{i//N}H{i%N}V")
    # print("sates:", self.state_labels)
    for i in range(dim**num_systems):
        new_label = ""
        for j in range(num_systems-1, -1, -1):
            # print("appending to labels:", f"{self.state_labels[(i//self.dim**j)%self.dim]}_{chr(65+j)} ")
            new_label += f"{state_labels[(i//dim**j)%dim]}_{chr(65+j)} "
        labels.append(new_label[:-1])
    return labels

def read_quantum_state(TN_state, N, num_states = 4, return_dense = False, precision = 10):
    dense_state = TN_state.to_dense()
    if return_dense: return dense_state
    dense_state = np.reshape(dense_state.data, (-1, 1), order = 'C')
    dense_state = sp.csr_matrix(dense_state)
    dense_state.data = np.round(dense_state.data, precision)
    dense_state.eliminate_zeros()

    print_quantum_state(N, dense_state, num_states)

def print_quantum_state(N, dense_state, num_states = 4):
    labels = generate_labels(num_states,N)
    state = dense_state.nonzero()[0]
    print("Corresponding Basis terms:")
    for k in state: print(labels[k],"-",k,"-",dense_state[k].data)

def create_ladder_MPO(site, total_sites, N, tag="$Ladder$"):
    a = qt.destroy(N).full()
    a_dag = a.T
    TMSV_MPO = mpo.from_dense(a_dag, dims = N, sites = (site,), L=total_sites, tags=tag) 
    # return TMSV_MPO.fill_empty_sites(mode = "minimal")
    return TMSV_MPO

def create_MPO(site1, site2, total_sites, op, N, tag):
    MPO = mpo.from_dense(op, dims = N, sites = (site1,site2), L=total_sites, tags=tag)
    # new_arrays = []
    # for i in range(len(MPO.arrays)):
    #     if len(MPO.arrays[i].shape) == 3:
    #         new_arrays.append(MPO.arrays[i].reshape(-1, N, N))
    # # TMSV_MPO=mpo(TMSV_MPO.arrays)
    # MPO = mpo(new_arrays)
    # for i in MPO.arrays:
    #     print(i.shape)
    # print("Inside op")
    
    return MPO

# Beamsplitter transformation
def create_BS_MPO(site1, site2, theta, total_sites, N, tag = 'BS'): 

    a = qt.destroy(N).full()
    a_dag = a.T
    I = np.eye(N)
    
    # This corresponds to the BS hamiltonian:

    hamiltonian_BS = -theta * ( kron(I, a_dag)@kron(a, I) - kron(I, a)@kron(a_dag, I) )
    unitary_BS = expm(hamiltonian_BS)

    # print("unitary_BS", unitary_BS)

    BS_MPO = mpo.from_dense(unitary_BS, dims = N, sites = (site1,site2), L=total_sites, tags=tag)
    # BS_MPO = BS_MPO.fill_empty_sites(mode = "full")
    return BS_MPO


def generalized_mode_mixer(site1, site2, theta, phi, psi, lamda, total_sites, N, tag = 'MM'): 

    a = qt.destroy(N).full()
    a_dag = a.T
    I = np.eye(N)
    
    # This corresponds to the BS hamiltonian: This is a different difinition from the one in 
    # create_BS_MPO. This is because of how the generalized beamsplitter is defined in DOI: 10.1088/0034-4885/66/7/203 . 
    hamiltonian_BS = theta * (kron(a_dag, I)@kron(I, a) + kron(a, I)@kron(I, a_dag))
    unitary_BS = expm(-1j * hamiltonian_BS)

    # print("unitary_BS\n", np.round(unitary_BS, 4))

    pre_phase_shifter = np.kron(phase_shifter(N, phi[0]/2), phase_shifter(N, phi[1]/2))
    post_phase_shifter = np.kron(phase_shifter(N, psi[0]/2), phase_shifter(N, psi[1]/2))
    global_phase_shifter = np.kron(phase_shifter(N, lamda[0]/2), phase_shifter(N, lamda[1]/2))

    # This construction for the generalized beamsplitter is based on the description in paper DOI: 10.1088/0034-4885/66/7/203
    generalized_BS = global_phase_shifter @  (pre_phase_shifter @ unitary_BS @ post_phase_shifter)

    # print("generalized_BS\n", np.round(generalized_BS, 4))

    BS_MPO = mpo.from_dense(generalized_BS, dims = N, sites = (site1,site2), L=total_sites, tags=tag)
    # BS_MPO = BS_MPO.fill_empty_sites(mode = "full")
    return BS_MPO


def phase_shifter(N, theta):
    diag = [np.exp(1j * theta * i) for i in range(N)]
    return np.diag(diag, k=0)


###### POVM OPERATORS #######


# This is the actual function that generates the POVM operator.
def create_threshold_POVM_OP_Dense(efficiency, outcome, N):
    a = qt.destroy(N).full()
    a_dag = a.T
    create0 = a_dag * sqrt(efficiency)
    destroy0 = a * sqrt(efficiency)
    series_elem_list = [((-1)**i) * matrix_power(create0, (i+1)) @ matrix_power(destroy0, (i+1)) / factorial(i+1) for i in range(N-1)] # (-1)^i * a_dag^(i+1) @ a^(i+1) / (i+1)! = (-1)^(i+2) * a_dag^(i+1) @ a^(i+1) / (i+1)! since goes from 0->n
    # print(series_elem_list[0])
    dense_op = sum(series_elem_list)

    if outcome == 0:
        dense_op = np.eye(dense_op.shape[0]) - dense_op
    # print(sqrtm(dense_op))
    return dense_op

@lru_cache(maxsize=20)
def factorial(x):
    n = 1
    for i in range(2, x+1):
        n *= i
    return n

@lru_cache(maxsize=20)
def comb(n, k):
    return factorial(n) / (factorial(k) * factorial(n - k))

@lru_cache(maxsize=20)
def projector(n, N):
    state = np.zeros(N)
    state[n] = 1
    return np.outer(state, state)

# Testing stuff out here. 
def create_PNR_POVM_OP_Dense(eff, outcome, N, debug = False):
    a_dag = qt.create(N).full()
    vacuum = np.zeros(N)
    vacuum[0] = 1

    @lru_cache(maxsize=20)
    def create_povm_list(eff, N):
        povms = []
        # m is the outcome here
        for m in range(N-1):
            op = 0
            for n in range(m, N):
                op += comb(n,m) * eff**m * (1-eff)**(n-m) * projector(n, N)
            povms.append(op)

        povms.append(np.eye(N) - sum(povms))
        return povms
    
    povms = create_povm_list(eff, N)
    if debug:
        return povms[outcome], povms
    return povms[outcome]



def generate_sqrt_POVM_MPO(sites, outcome, total_sites, efficiency, N, pnr = False, tag = "POVM"):
    if pnr:
        dense_op = sqrtm(create_PNR_POVM_OP_Dense(efficiency, outcome, N)).astype(np.complex128)
    else:
        dense_op = sqrtm(create_threshold_POVM_OP_Dense(efficiency, outcome, N)).astype(np.complex128)

    sqrt_POVM_MPOs = []
    for i in sites:
        sqrt_POVM_MPOs.append(mpo.from_dense(dense_op, dims = N, sites = (i,), L=total_sites, tags=tag))

    return sqrt_POVM_MPOs



########## TMSV Operator ############

# TMSV operator
def old_create_TMSV_OP_Dense(N, mean_photon_num):

    a = qt.destroy(N).full()
    a_dag = a.T
    truncation = (N-1)      

    def generate_amp_list(mean_photon_num):
        amp_list = [(sqrt(mean_photon_num / (mean_photon_num + 1)) ** m) / sqrt(mean_photon_num + 1) for m in range(truncation)]
        amp_square_list = [amp ** 2 for amp in amp_list]
        amp_list.append(sqrt(1 - sum(amp_square_list)))
        return amp_list

    amp = generate_amp_list(mean_photon_num)

    op = np.complex128(0)
    for i in range(truncation+1):
        # TMSV is a 2 mode state (independent spatial modes). Hence, we take the tensor product of the two mode operators
        new_op = amp[i] * ( matrix_power(kron(a_dag, a_dag), i) ) / factorial(i)
        op += new_op

    return op

def create_TMSV_OP_Dense(N, mean_photon_num):
    a = qt.destroy(N).full()
    a_dag = a.T
    truncation = (N-1)   

    op = expm(1j * mean_photon_num * (kron(a_dag, a_dag) + kron(a, a)))

    return op



########## Light Source ###########

def light_source(vacuum, N, mean_photon_num, num_modes, error_tolerance, TMSV_indices = ((0,2),(5,7)), compress = True, contract = True):

    psi = vacuum.copy()
    psi.add_tag("L0")
    site_tags = psi.site_tags

    # Creating TMSV ops:
    TMSV_op_dense = create_TMSV_OP_Dense(N, mean_photon_num)

    TMSV_MPO_H = create_MPO(site1 = TMSV_indices[0][0], site2 = TMSV_indices[0][1], total_sites = num_modes, op = TMSV_op_dense, N = N, tag = r"$TMSV_H$")
    # TMSV_MPO_H.draw()
    # print("sites present in light_source:", TMSV_MPO_H.sites)
    enforce_1d_like(TMSV_MPO_H, site_tags=site_tags, inplace=True)
    # print("sites present in light_source:", TMSV_MPO_H.sites)
    TMSV_MPO_H.add_tag("L1")

    TMSV_MPO_V = create_MPO(site1 = TMSV_indices[1][0], site2 = TMSV_indices[1][1], total_sites = num_modes, op = TMSV_op_dense, N = N, tag = r"$TMSV_V$")
    enforce_1d_like(TMSV_MPO_V, site_tags=site_tags, inplace=True)
    TMSV_MPO_V.add_tag("L1")

    # Creating PBS ops:
    U_PBS_H_Signal = create_BS_MPO(site1 = 2, site2 = 6, theta=np.pi/2, total_sites = num_modes, N = N, tag = r"$PBS_S$")
    enforce_1d_like(U_PBS_H_Signal, site_tags=site_tags, inplace=True)
    U_PBS_H_Signal.add_tag("L1")

    U_PBS_H_Idler = create_BS_MPO(site1 = 0, site2 = 4, theta=np.pi/2, total_sites = num_modes, N = N, tag = r"$PBS_I$")
    enforce_1d_like(U_PBS_H_Idler, site_tags=site_tags, inplace=True)
    U_PBS_H_Signal.add_tag("L1")

    # Create entangled state:
    psi = tensor_network_apply_op_vec(TMSV_MPO_H, psi, compress=compress, contract = contract, cutoff = error_tolerance)
    psi = tensor_network_apply_op_vec(TMSV_MPO_V, psi, compress=compress, contract = contract, cutoff = error_tolerance)
    psi = tensor_network_apply_op_vec(U_PBS_H_Idler, psi, compress=compress, contract = contract, cutoff = error_tolerance)
    psi = tensor_network_apply_op_vec(U_PBS_H_Signal, psi, compress=compress, contract = contract, cutoff = error_tolerance)

    psi.normalize()

    # print("trace is:", np.linalg.norm(psi.to_dense()))

    for _ in range(4):
        psi.measure(0, remove = True, renorm = True, inplace = True)

    # Not used for TN implermentation. Used for validating impelmentation with dense version
    TMSV_state = psi.to_dense()
    TMSV_state = np.reshape(TMSV_state.data, (-1, 1), order = 'C')
    TMSV_state = sp.csr_matrix(TMSV_state)
    TMSV_state.data = np.round(TMSV_state.data, 10)
    TMSV_state.eliminate_zeros()

    return psi, TMSV_state

def new_ls(N, mean_photon_num, error_tolerance, compress = True, contract = True):
    trunc = N-1
    spdc = seq_ls.SPDCSource("", Timeline(formalism=POLARIZATION_FOCK_FORMALISM, truncation = trunc), mean_photon_num=mean_photon_num)
    dense_state = spdc._generate_tmsv_state(dm = False).toarray()

    psi = mps.from_dense(psi = dense_state, dims = N, tags = "ENT", cutoff = error_tolerance)
    return psi


# Generate truncation filter MPO 
# TODO: Make a function to renormalize a quantum state. How: find the projection of the quantum state onto itself and calculate the 
# probability. Next, take the square root of this number, divide it by the number nodes in the quantum state and multiply it with 
# all the states in the MPS. For density matrices, simply find the trace directly and do the same thing as the previous example except
# for not taking the square root.  The truncation filter would not work without the renormalization 
def create_truncation_filter_Dense(truncation):
    # This is only the projection operator. The states need to be normalized first. 
    N = truncation+1
    vacuum = np.zeros(N**2)
    vacuum[0] = 1

    a = qt.destroy(N).full()
    a_dag = a.T
    I = np.eye(N)

    # # debug
    # labels = generate_labels(1,N)

    op = 0
    for trunc in range(truncation, -1, -1):
        state = kron(matrix_power(a_dag, trunc), I) @ vacuum / sqrt(factorial(trunc) * factorial(0))
        op+=np.outer(state, state)
        coeffs = [trunc+1, 0]

        # # Debug
        # state_inds = state.nonzero()[0]
        # print("TMSV state:", [labels[i] for i in state_inds], "Val:", state[state_inds[0]])
        # print("coeffs", coeffs)

        for i in range(trunc):
            coeffs = [coeffs[0]-1, coeffs[1]+1]
            state = kron(a, a_dag) @ state / sqrt((coeffs[0]) * (coeffs[1]))
            op += np.outer(state, state)


            # # debug
            # state_inds = state.nonzero()[0]
            # print("TMSV state:", [labels[i] for i in state_inds], "Val:", state[state_inds[0]])
            # print("coeffs", coeffs)

    return op




########## EXTEND MPS ###########

def extend_MPS(psi, psi_second = None):
    # print("inside extend_MPS")
    # psi_second.draw()
    # print(psi_second)
    
    psi.permute_arrays('lrp')

    # psi_second.draw()
    # print(psi_second)

    # This is supposed to be passed as the second MPS to extend the first MPS with. 
    if psi_second == None:
        psi_second = psi.copy()
    else:
        psi_second.permute_arrays('lrp')
    
    psi_num_modes = len(psi.site_tags)
    psi2_num_modes = len(psi_second.site_tags)

    psi_second.reindex({f"k{i}":f"k{i+psi_num_modes}" for i in range(psi2_num_modes)}, inplace = True)
    psi_second.retag({f"I{i}":f"I{i+psi_num_modes}" for i in range(psi2_num_modes)}, inplace = True)

    psi = psi.combine(psi_second)

    psi_last_tensor = psi.select_tensors(f"I{psi_num_modes-1}", which='any')[0]
    psi2_first_tensor = psi.select_tensors(f"I{psi_num_modes}", which='any')[0]

    new_bond(psi2_first_tensor, psi_last_tensor, axis1=0, axis2=1)

    # Simply find the tags for the input modes. 
    pattern = re.compile(r"I[0-9][0-9]*")
    tags = []
    for tag_list in [t.tags for t in psi]:
        for tag in tag_list:
            match = re.search(pattern, tag)
            if match:
                tags.append(match.string)
                break
            
    # print(tags)

    # for i,j in zip(psi.arrays, tags):
    #     print(i.shape, j, int(j[1:]))

    sorted_arrays = [array for array, _ in sorted( zip(psi.arrays, tags), key = lambda pair: int(pair[1][1:]) )]

    # for array in sorted_arrays:
    #     print(array.shape)

    psi = mps(sorted_arrays)

    # psi.add_tag("L1")
    # psi.add_tag(r'$HH+VV$')

    # print("outside extend_MPS")

    return psi

# psi = extend_MPS(psi)



########## SWAP OPERATORS ############

# def bell_state_measurement(psi, N, site_tags, num_modes, efficiency, error_tolerance, beamsplitters = [[2,6],[3,7]], measurements = {1:(2,7), 0:(3,6)}, pnr = False, compress = True, contract = True):

#     U_BS_H = create_BS_MPO(site1 = beamsplitters[0][0], site2 = beamsplitters[0][1], theta=np.pi/4, total_sites = num_modes, N = N, tag = r"$U_{BS_H}$")
#     enforce_1d_like(U_BS_H, site_tags=site_tags, inplace=True)
#     U_BS_H.add_tag("L2")

#     U_BS_V = create_BS_MPO(site1 = beamsplitters[1][0], site2 = beamsplitters[1][1], theta=np.pi/4, total_sites = num_modes, N = N, tag = r"$U_{BS_V}$")
#     enforce_1d_like(U_BS_V, site_tags=site_tags, inplace=True)
#     U_BS_V.add_tag("L3")

#     BSM_POVM_1_OPs = generate_sqrt_POVM_MPO(sites=measurements[1], outcome = 1, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr)
#     BSM_POVM_1_OPs.extend(generate_sqrt_POVM_MPO(sites=measurements[0], outcome = 0, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr))


#     psi = tensor_network_apply_op_vec(U_BS_H, psi, compress=compress, contract = contract, cutoff = error_tolerance)
#     psi = tensor_network_apply_op_vec(U_BS_V, psi, compress=compress, contract = contract, cutoff = error_tolerance)

#     for POVM_OP in BSM_POVM_1_OPs:
#         POVM_OP.add_tag("L4")
#         psi = tensor_network_apply_op_vec(POVM_OP, psi, compress=compress, contract = contract, cutoff = error_tolerance)

#     return psi

def bell_state_measurement(psi, N, site_tags, num_modes, efficiency, error_tolerance, measurements = {1:(2,7), 0:(3,6)}, pnr = False, det_outcome = 1, return_MPOs = False, compress = True, contract = True):

    """Perform Bell state measrement or return the MPOs used in the measurement.
    Args:
        psi (mps): The input state to be measured.
        N (int): local Hilbert space dimension
        site_tags (list): The tags for the sites in the MPS.
        num_modes (int): The number of modes in the MPS.
        efficiency (float): The efficiency of the detectors.
        error_tolerance (float): The error tolerance for the tensor network.
        measurements (dict): The sites for the measurements. Default is {1:(2,7), 0:(3,6)}.
        pnr (bool): Whether to use photon number resolving measurement. Default is False.
        pnr_outcome (int): The outcome for the photon number resolving measurement. Default is 1. When not using PNR, this can be anything other than 1 since threshold detectors don't distinguish between photon numbers. 
        return_MPOs (bool): Whether to return the MPOs used in the measurement. Default is False.
        compress (bool): Whether to compress the MPS after applying the MPOs. Default is True.
        contract (bool): Whether to contract the MPS after applying the MPOs. Default is True.
        
        Returns:
            mps: The measured state after the Bell state measurement.
            
    """

    U_BS_H = create_BS_MPO(site1 = 2, site2 = 6, theta=np.pi/4, total_sites = num_modes, N = N, tag = r"$U_{BS_H}$")
    enforce_1d_like(U_BS_H, site_tags=site_tags, inplace=True)
    U_BS_H.add_tag("L2")

    U_BS_V = create_BS_MPO(site1 = 3, site2 = 7, theta=np.pi/4, total_sites = num_modes, N = N, tag = r"$U_{BS_V}$")
    enforce_1d_like(U_BS_V, site_tags=site_tags, inplace=True)
    U_BS_V.add_tag("L3")

    BSM_POVM_1_OPs = generate_sqrt_POVM_MPO(sites=measurements[1], outcome = det_outcome, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr)
    BSM_POVM_1_OPs.extend(generate_sqrt_POVM_MPO(sites=measurements[0], outcome = 0, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr))

    if return_MPOs:
        returned_MPOs = [U_BS_H, U_BS_V]
        returned_MPOs.extend(BSM_POVM_1_OPs) # Collect all the MPOs in a list and return them. The operators are ordered as such: 
        return returned_MPOs

    psi = tensor_network_apply_op_vec(U_BS_H, psi, compress=compress, contract = contract, cutoff = error_tolerance)
    psi = tensor_network_apply_op_vec(U_BS_V, psi, compress=compress, contract = contract, cutoff = error_tolerance)

    for POVM_OP in BSM_POVM_1_OPs:
        POVM_OP.add_tag("L4")
        psi = tensor_network_apply_op_vec(POVM_OP, psi, compress=compress, contract = contract, cutoff = error_tolerance)

    return psi



def rotate_and_measure(psi, N, site_tags, num_modes, efficiency, error_tolerance, idler_angles, signal_angles, rotations = {"signal":(4,5), "idler":(0,1)}, measurements = {1:(0,4), 0:(1,5)}, pnr = False, det_outcome = 1, return_MPOs = False, compress = True, contract = True, draw = False):
    # idler_angles = [0]
    # angles = [np.pi/4]

    # We make this correction here since the rotator hamiltonian is 1/2(a_v b_h + a_h b_v), which does not show up in the bs unitary, whose function we are reusing to 
    # rotate the state.
    idler_angles = idler_angles/2
    signal_angles = signal_angles/2

    coincidence = []

    POVM_1_OPs = generate_sqrt_POVM_MPO(sites = measurements[1], outcome = det_outcome, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr)
    POVM_0_OPs = generate_sqrt_POVM_MPO(sites = measurements[0], outcome = 0, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr)
    # POVM_0_OPs = generate_sqrt_POVM_MPO(sites=(0,4), outcome = 0, total_sites=num_modes, efficiency=efficiency, N=N, pnr = pnr)
    # enforce_1d_like(POVM_OP, site_tags=site_tags, inplace=True)

    meas_ops = POVM_1_OPs
    meas_ops.extend(POVM_0_OPs)

    for i, idler_angle in enumerate(idler_angles):
        coincidence_probs = []

        rotator_node_1 = create_BS_MPO(site1 = rotations["idler"][0], site2 = rotations["idler"][1], theta=idler_angle, total_sites = num_modes, N = N, tag = r"$Rotator_I$")
        enforce_1d_like(rotator_node_1, site_tags=site_tags, inplace=True)
        rotator_node_1.add_tag("L5")
        if not return_MPOs: # If the user wants the MPOs, we don't need to apply the rotator to the state.
            idler_rotated_psi = tensor_network_apply_op_vec(rotator_node_1, psi, compress=compress, contract = contract, cutoff = error_tolerance)


        for j, angle in enumerate(signal_angles):
            # print("idler:", i, "signal:", j)
        
            rotator_node_2 = create_BS_MPO(site1 = rotations["signal"][0], site2 = rotations["signal"][1], theta=angle, total_sites = num_modes, N = N, tag = r"$Rotator_S$")
            enforce_1d_like(rotator_node_2, site_tags=site_tags, inplace=True)

            if return_MPOs:
                meas_ops.extend([rotator_node_1, rotator_node_2]) # Collect all the MPOs in a list and return them
                return meas_ops
        
            # Rotate and measure:
            rotator_node_2.add_tag("L5")
            rho_rotated = tensor_network_apply_op_vec(rotator_node_2, idler_rotated_psi, compress=compress, contract = contract, cutoff = error_tolerance)

            # read_quantum_state(psi)
            # read_quantum_state(rho_rotated)

            for POVM_OP in meas_ops:
                POVM_OP.add_tag("L6")
                rho_rotated = tensor_network_apply_op_vec(POVM_OP, rho_rotated, compress=compress, contract = contract, cutoff = error_tolerance)
        
            if draw:
                # only for drawing the TN. Not used otherwise
                fix = {(f"L{j}",f"I{num_modes - i-1}"):(3*j,i+5) for j in range(10) for i in range(10)}
                rho_rotated.draw(color = [r'$HH+VV$', r'$U_{BS_H}$', r"$U_{BS_V}$", 'POVM', r'$Rotator_I$', r'$Rotator_S$'], title = "Polarization entanglement swapping MPS", fix = fix, show_inds = True, show_tags = False)
                # rho_rotated.draw_tn()
            coincidence_probs.append((rho_rotated.norm())**2)
        coincidence.append(coincidence_probs)
    
    return np.array(coincidence)

# coincidence = rotate_and_measure(psi, N, psi.site_tags, num_modes, efficiency, error_tolerance)


def calc_fidelity_swapping(state, reference_state, N, error_tolerance):
    reference_mps = create_polarization_bell_state(reference_state, N)
    projector_mpo = outer_product_mps(reference_mps)

    projector_mpo.reindex({"k0":"k0","k1":"k1","k2":"k4","k3":"k5"}, inplace = True)
    projector_mpo.reindex({"b0":"b0","b1":"b1","b2":"b4","b3":"b5"}, inplace = True)
    projector_mpo.retag({"I0":"I0","I1":"I1","I2":"I4","I3":"I5"}, inplace = True)

    # print("sites present in projector_mpo:", projector_mpo.sites)
    enforce_1d_like(projector_mpo, site_tags=state.site_tags, inplace=True)
    # print("sites present in projector_mpo:", projector_mpo.sites)

    # print("projector.lower_ind_id", projector_mpo.lower_inds, "projector.upper_ind_id", projector_mpo.upper_inds)

    
    # for site in projector_mpo.gen_site_coos():
    #     print(site)


    # projector_mpo.draw()
    # state.draw()
    state = tensor_network_apply_op_vec(projector_mpo, state, compress=True, contract = True, cutoff = error_tolerance)
    # state.draw()
    return state.norm()**2

    
    
    # Calculate and return fidelity of the projected state. 


def create_polarization_bell_state(bell_state, N, error_tolerance = 1e-12):
    I = np.eye(N)

    a_dag = qt.create(N).full()
    a = qt.destroy(N).full()

    vacuum_state = np.zeros((N,1))
    vacuum_state[0] = 1
    vac_projector = np.outer(vacuum_state, vacuum_state)

    one_state = a_dag @ vacuum_state # For now, we're defining the 1 state as having only one photon. This could be changed to have any number of non-zero photons.
    # print("one_state:", one_state)   # This is because the ideal case is having exactly one photon for the 1 state. 
    one_projector = np.outer(one_state, one_state)                                 

    NOT_gate = vacuum_state @ one_state.conj().T + one_state @ vacuum_state.conj().T
    H_gate = (1/sqrt(2)) * ((vacuum_state - one_state) @ one_state.conj().T + (vacuum_state + one_state) @ vacuum_state.conj().T)
    C_NOT_close = np.kron(vac_projector, I) + np.kron(one_projector, NOT_gate)
    C_NOT_open = np.kron(one_projector, I) + np.kron(vac_projector, NOT_gate)

    NOT_MPO_0 = mpo.from_dense(NOT_gate, dims = N, sites = (0,), L=4, tags="a_dag")
    NOT_MPO_1 = mpo.from_dense(NOT_gate, dims = N, sites = (1,), L=4, tags="a_dag")
    H_MPO = mpo.from_dense(H_gate, dims = N, sites = (0,), L=4, tags="H")
    C_NOT_close_MPO_1 = mpo.from_dense(C_NOT_close, dims = N, sites = (0,1), L=4, tags="C_NOT_close_1")
    C_NOT_close_MPO_2 = mpo.from_dense(C_NOT_close, dims = N, sites = (1,2), L=4, tags="C_NOT_close_2")
    C_NOT_open_MPO = mpo.from_dense(C_NOT_open, dims = N, sites = (2,3), L=4, tags="C_create_open")
    
    vacuum = create_vacuum_state(4, N, bond_dim = 2)

    if bell_state == "psi_minus":
        psi = tensor_network_apply_op_vec(NOT_MPO_0, vacuum, compress=True, contract = True, cutoff = error_tolerance)
        psi = tensor_network_apply_op_vec(NOT_MPO_1, psi, compress=True, contract = True, cutoff = error_tolerance)
    elif bell_state == "psi_plus":
        psi = tensor_network_apply_op_vec(NOT_MPO_1, vacuum, compress=True, contract = True, cutoff = error_tolerance)
    elif bell_state == "phi_plus":
        psi = vacuum
    elif bell_state == "phi_minus":
        psi = tensor_network_apply_op_vec(NOT_MPO_0, vacuum, compress=True, contract = True, cutoff = error_tolerance)

    
    psi = tensor_network_apply_op_vec(H_MPO, psi, compress=True, contract = True, cutoff = error_tolerance)
    # read_quantum_state(psi, N, num_states = 2)
    psi = tensor_network_apply_op_vec(C_NOT_close_MPO_1, psi, compress=True, contract = True, cutoff = error_tolerance)
    # read_quantum_state(psi, N, num_states = 2)
    psi = tensor_network_apply_op_vec(C_NOT_close_MPO_2, psi, compress=True, contract = True, cutoff = error_tolerance)
    psi = tensor_network_apply_op_vec(C_NOT_open_MPO, psi, compress=True, contract = True, cutoff = error_tolerance)
    
    return psi


def outer_product_mps(psi):
    psi_H = psi.H
    psi_H.retag_({'In': 'Out'})
    psi_H.site_ind_id = 'b{}'
    rho = (psi_H | psi)
    for i in range(rho.L):
        rho ^= f"I{i}"   
    rho = TensorNetwork1DOperator(rho)
    rho._upper_ind_id = psi.site_ind_id
    rho._lower_ind_id = psi_H.site_ind_id
    rho = rho.fuse_multibonds()
    rho_MPO = rho.view_as_(mpo, cyclic = False, L = 8) # L is important. Its hard coded now, but must be configutrable based on the input state. 
    return rho_MPO


def plot_coincidences(coincidence, idler_angles, signal_angles, title = ''):
    visibilities = []
    for i in range(len(coincidence)):
        visibility = (max(coincidence[i]) - min(coincidence[i])) / (max(coincidence[i]) + min(coincidence[i]))
        visibilities.append(visibility)
        # print(visibility, coincidence[i])

    idler_angles = np.array(list(map(float, idler_angles)))/np.pi

    plt.figure()
    plt.grid(True)
    for i in range(len(idler_angles)):
        # print(fringe_real[i])
        plt.plot(signal_angles, coincidence[i], label=r'{:.2f}$\pi$'.format(idler_angles[i]))
    plt.title(title)
    plt.ylabel("Coincidence probability")
    plt.xlabel(r"$\alpha$ (rad)")    
    plt.legend(title = "$\delta$")

    plt.figure()
    plt.grid(True)
    plt.plot(idler_angles*np.pi, visibilities)
    plt.title("Visiblilities")
    plt.ylabel("Visibility")
    plt.xlabel(r"$\delta$")    
