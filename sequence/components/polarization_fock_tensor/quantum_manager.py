
from __future__ import annotations
from abc import abstractmethod
from typing import List, Dict, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from ...components.circuit import Circuit
    from ...kernel.quantum_state import State

from qutip.qip.circuit import QubitCircuit, Gate
from qutip.qip.operations import gate_sequence_product
from numpy import log, array, cumsum, base_repr, zeros
from scipy.sparse import csr_matrix
from scipy.special import binom
import time
import numpy as np
import scipy.sparse as sp

from numpy.linalg import matrix_power
import qutip as qt
from math import factorial


from quimb.tensor import MatrixProductState as mps  # type: ignore
from quimb.tensor.tensor_core import rand_uuid, new_bond  # type: ignore
from quimb.tensor import MatrixProductOperator as mpo  # type: ignore
from quimb.tensor.tensor_arbgeom import  tensor_network_apply_op_vec # type: ignore

from ...kernel.quantum_utils import *
from ...kernel.quantum_manager import QuantumManagerDensityFock, DENSITY_MATRIX_FORMALISM
from sequence.components.polarizationFock_Tensor.quantum_state import Matrix_Product_State





def extract_sparse_data(matrix):
    values = tuple(matrix.data)
    x_indices, y_indices = tuple(map(tuple, matrix.nonzero()))
    return (values, (x_indices, y_indices))


# def create_spare_matrix(data, dim, num_systems):
#     """
#     Creates sparse matrix using the data extracted from the "extract_sparse_data" method 
#     above or from data formatted in the same way. 
#     """
#     return sp.csr_matrix(data, (dim**num_systems, dim**num_systems))


@lru_cache(maxsize=100)
def _build_amp_damping_kraus_operators(loss_rate: float, N: int):
    V = []
    basis = sp.eye(N**2, format="csc")
    for k in range(N**2):
        op_subsystem = 0
        k1 = np.floor(k/N)
        k2 = k % N
        for n in range(0,N**2):

            n1 = np.floor(n/N)
            n2 = n % N

            if not ((n1>=k1) and (n2>=k2)):
                continue

            m = int((n1-k1)*N + (n2-k2))
            op_subsystem += sqrt(binom(n1, k1) * binom(n2, k2)) * np.cos(loss_rate)**(n1+n2-k1-k2) * (-1j*np.sin(loss_rate))**(k1+k2) * basis[:,m]*basis[:,n].transpose()                
        
        V.append(sp.csr_matrix(op_subsystem))
    return V



class QuantumManagerPolarizationFockTensor(QuantumManagerDensityFock):
    def __init__(self, truncation: int = 1, error_tolerance = 1e-10):
        # default truncation is 1 for 2-d Fock space.
        super().__init__(truncation=truncation)
        self.N = truncation+1
        self.dim = self.N**2
        self.error_tolerance = error_tolerance
        # self.basis = sp.csr_matrix(np.eye(self.dim))
        # self.basis = tuple(map(tuple, np.eye(self.dim)))
        self.generate_mode_operators()

        self.extract_sparse_data = extract_sparse_data
        self.create_spare_matrix = lambda data: create_spare_matrix(data, self.dim)

        self.state_labels = []
        for i in range(self.dim):
            self.state_labels.append(f"{i//self.N}H{i%self.N}V")

        # For benchmaring number of non-zero elements in density matrix
        self.largest_dm_size = 0
        self.largest_dm_dims = 0


    def generate_labels(self, num_systems):
        labels = []
        # print("sates:", self.state_labels)
        for i in range(self.dim**num_systems):
            new_label = ""
            for j in range(num_systems-1, -1, -1):
                # print("appending to labels:", f"{self.state_labels[(i//self.dim**j)%self.dim]}_{chr(65+j)} ")
                new_label += f"{self.state_labels[(i//self.dim**j)%self.dim]}_{chr(65+j)} "
            labels.append(new_label[:-1])
        return labels


    def generate_mode_operators(self):
        a = sp.diags(diagonals = np.sqrt(np.arange(1,self.N)), offsets = 1)
        a_dag = a.T
        I = sp.eye(self.N)

        self.a_H = sp.kron(a, I, "csr")
        self.a_V = sp.kron(I, a, "csr")
        self.adag_H = sp.kron(a_dag, I, "csr")
        self.adag_V = sp.kron(I, a_dag, "csr")


    # def _apply_kraus_operators(self, prepared_state, all_keys, kraus_ops, verbose = False):
    #     output_state = sp.csr_matrix(prepared_state.shape, dtype=complex)

    #     # print("prepared_state.type", type(prepared_state), "kraus_ops[0]", type(kraus_ops[0]))

    #     for kraus_op in kraus_ops:
    #         output_state += kraus_op @ prepared_state @ kraus_op.conj().T
        
    #     # print("output:", type(output_state))
    #     if verbose:
    #         print(output_state)
    #     self.set(all_keys, output_state)

    # def add_loss(self, key, loss_rate, verbose = False):
    #     prepared_state, all_keys = self._prepare_state([key])
    #     local_kraus_ops = _build_amp_damping_kraus_operators(loss_rate, self.N)
    #     kraus_ops = [self._prepare_operator(all_keys, [key], op_subsystem) for op_subsystem in local_kraus_ops]
    #     self._apply_kraus_operators(prepared_state, all_keys, kraus_ops, verbose)

    # Updated
    def new(self, state=None) -> int:
        """Method to create a new state with key

        Args:
            state (Union[str, List[complex], List[List[complex]]]): amplitudes of new state.
                Default value is 'gnd': create zero-excitation state with current truncation.
                Other inputs are passed to the constructor of `DensityState`.
        """

        key = self._least_available
        self._least_available += 1

        # If the input state is None, it is kept none. The state must be set manually.
        # This is since extending tensor networks is difficult. 
        self.states[key] = Matrix_Product_State(state, [key], truncation=self.truncation)

        return key
    
    # Updated
    def set(self, keys: List[int], state):
        # state_data = self.extract_sparse_data(state)
        new_state = Matrix_Product_State(state, keys, truncation=self.truncation)
        
        for key in keys:
            self.states[key] = new_state



    def extend_MPS(self, psi, psi_second):
        psi.permute_arrays('lrp')
        psi_second.permute_arrays('lrp')
        
        psi_num_modes = len(psi.site_tags)
        psi2_num_modes = len(psi_second.site_tags)

        psi_second.reindex({f"k{i}":f"k{i+psi_num_modes}" for i in range(psi2_num_modes)}, inplace = True)
        psi_second.retag({f"I{i}":f"I{i+psi_num_modes}" for i in range(psi2_num_modes)}, inplace = True)

        psi = psi.combine(psi_second)

        psi_last_tensor = psi.select_tensors(f"I{psi_num_modes-1}", which='any')[0]
        psi2_first_tensor = psi.select_tensors(f"I{psi_num_modes}", which='any')[0]

        new_bond(psi2_first_tensor, psi_last_tensor, axis1=0, axis2=1)

        pattern = re.compile(r"I[0-9][0-9]*")
        tags = []
        for tag_list in [t.tags for t in psi]:
            for tag in tag_list:
                match = re.search(pattern, tag)
                if match:
                    tags.append(match.string)
                    break
                
        sorted_arrays = [array for array, _ in sorted(zip(psi.arrays, tags), key = lambda pair: pair[1])]

        psi = mps(sorted_arrays)

        psi.add_tag("L1")
        psi.add_tag(r'$HH+VV$')

        return psi

    # Basically, the only job of this method is to concatenate two hilbert spaces into a larger hilbert space and return the 
    # set of all_keys in the overall state. 
    # UNTESTED
    def _prepare_state(self, keys: List[int]):
        """Function to prepare states at given keys for operator application.

        Will take composite quantum state and swap subsystems to correspond with listed keys.
        Should not be called directly, but from method to apply operator or measure state.

        Args:
            keys (List[int]): keys for states to apply operator to.

        Returns:
            Tuple(List[List[complex]], List[int]): Tuple containing:
                1. new state to apply operator to, with keys swapped to be consecutive.
                2. list of keys corresponding to new state.
        """

        old_states = []
        all_keys = []

        # go through keys and get all unique qstate objects
        for key in keys:
            qstate = self.states[key]
            if qstate.keys[0] not in all_keys:
                old_states.append(qstate.state)
                all_keys += qstate.keys

        # construct compound state
        new_psi = old_states[0]

        if len(old_states) > 1:
            for i in range(1,len(old_states)):
                new_psi = self.extend_MPS(new_psi, old_states[i])
                           
        return new_psi, all_keys
        # new_state = [1]
        # for state in old_states:
        #     new_state = kron(new_state, state)

        ########### TN implementation does not have a desired key order since applying measurements in 
        ########### TNs is very easy. 

        # # apply any necessary swaps to order keys
        # if len(keys) > 1:

        #     # generate desired key order
        #     start_idx = all_keys.index(keys[0])
        #     if start_idx + len(keys) > len(all_keys):
        #         start_idx = len(all_keys) - len(keys)

        #     for i, key in enumerate(keys):
        #         i = i + start_idx
        #         j = all_keys.index(key)
        #         if j != i:
        #             swap_unitary = self._generate_swap_operator(len(all_keys), i, j)
        #             new_state = swap_unitary @ new_state @ swap_unitary.T
        #             all_keys[i], all_keys[j] = all_keys[j], all_keys[i]


    # We don't need to prepare operators for TNs. They are applied simply as local operations and don't require 
    # tensor producting identities or anything. 
    # # Not doing for now
    # def _prepare_operator(self, all_keys: List[int], keys: List[int], operator):
    #     # pad operator with identity
    #     left_dim = self.dim ** all_keys.index(keys[0])
    #     right_dim = self.dim ** (len(all_keys) - all_keys.index(keys[-1]) - 1)
    #     prepared_operator = operator

    #     # print("befire prep op:", type(operator))

    #     if left_dim > 0:
    #         prepared_operator = sp.kron(sp.eye(left_dim), prepared_operator)
    #     if right_dim > 0:
    #         prepared_operator = sp.kron(prepared_operator, sp.eye(right_dim))

    #     # print("after prep op:", type(prepared_operator))
    #     return sp.csr_matrix(prepared_operator)

    @lru_cache(maxsize=100)
    def create_POVM_OP_Dense(self, efficiency, outcome, N):
        a = qt.destroy(N).full()
        a_dag = a.T
        create0 = a_dag * sqrt(efficiency)
        destroy0 = a * sqrt(efficiency)
        series_elem_list = [((-1)**i) * matrix_power(create0, (i+1)) @ matrix_power(destroy0, (i+1)) / factorial(i+1) for i in range(N-1)] # (-1)^i * a_dag^(i+1) @ a^(i+1) / (i+1)! = (-1)^(i+2) * a_dag^(i+1) @ a^(i+1) / (i+1)! since goes from 0->n
        # print(series_elem_list[0])
        dense_op = sum(series_elem_list)

        if outcome == 0:
            dense_op = np.eye(dense_op.shape[0]) - dense_op
        # print(dense_op)
        return dense_op

    def generate_POVM_MPO(self, sites, outcomes, total_sites, efficiencies, N, tag = "POVM"):
        
        assert len(sites) == len(outcomes) == len(efficiencies)

        POVM_MPOs = []
        for site,outcome,efficiency in zip(sites, outcomes, efficiencies):
            # Yo can make this more efficient by not performing the from_dense every time and simply applying the 
            # POVMs on the required sites. 
            dense_op = self.create_POVM_OP_Dense(efficiency, outcome, N)
            POVM_MPOs.append(mpo.from_dense(dense_op, dims = N, sites = (site,), L=total_sites, tags=tag))
            
        return POVM_MPOs    

    # Basic tested
    def measure(self, keys: List[int], TN_inds, outcomes = [], efficiencies = [], verbose = False) -> int:
        """Method to measure subsystems at given keys in POVM formalism.

        Serves as wrapper for private `_measure` method, performing quantum manager specific operations.

        Args:
            keys (List[int]): list of keys to measure.
            povms: (List[array]): list of POVM operators to use for measurement.
            meas_samp (float): random measurement sample to use for computing resultant state.
            verbose (boolean): Print out measurement state and probabilities.
        Returns:
            int: measurement as index of matching POVM in supplied tuple.
        """

        # state = self.states[keys[0]].state
        # print("type of state:", type(state))
        # print("len of dm while measuring:", len(state.nonzero()[0]))


        # new_state, all_keys = self._prepare_state(keys)

        # Assuming whaterver state you are measuring is already in one joint state and not the first key is sufficient to measure the entire state. 
        new_mps = self.states[keys[0]]

        # For now, we are assuming that all the states are being measured simultaneousoly and we are
        # not interestd in the post-measurement state of the system.  

        meas_ops = self.generate_POVM_MPO(TN_inds, outcomes, 2*len(keys), efficiencies, self.N, tag = "POVM")

        measured_mps = new_mps.state

        for POVM_OP in meas_ops:
            POVM_OP.add_tag("L6")
            measured_mps = tensor_network_apply_op_vec(POVM_OP, measured_mps, compress=True, contract = True, cutoff = self.error_tolerance)
        
        return (measured_mps.norm())**2, measured_mps # returning mps only for debugging
 
