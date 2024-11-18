
from __future__ import annotations
from abc import abstractmethod
from typing import List, Dict, TYPE_CHECKING

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
from matplotlib import pyplot as plt

from ...kernel.quantum_state import KetState, DensityState
from ...kernel.quantum_utils import *
from ...kernel.quantum_manager import QuantumManagerDensityFock, DENSITY_MATRIX_FORMALISM
from .quantum_state import SparseDensityState


def extract_sparse_data(matrix):
    values = tuple(matrix.data)
    x_indices, y_indices = tuple(map(tuple, matrix.nonzero()))
    return (values, (x_indices, y_indices))


def create_spare_matrix(data, dim, num_systems):
    """
    Creates sparse matrix using the data extracted from the "extract_sparse_data" method 
    above or from data formatted in the same way. 
    """
    return sp.csr_matrix(data, (dim**num_systems, dim**num_systems))


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
            op_subsystem += sqrt(binom(n1, k1) * binom(n2, k2)) * np.sqrt(1-loss_rate)**(n1+n2-k1-k2) * (-1j*np.sqrt(loss_rate))**(k1+k2) * basis[:,m]*basis[:,n].transpose()                
        
        V.append(sp.csr_matrix(op_subsystem))
    return V



class QuantumManagerPolarizationFock(QuantumManagerDensityFock):
    def __init__(self, truncation: int = 1):
        # default truncation is 1 for 2-d Fock space.
        super().__init__(truncation=truncation)
        self.N = truncation+1
        self.dim = self.N**2
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


    def _apply_kraus_operators(self, prepared_state, all_keys, kraus_ops, verbose = False):
        output_state = sp.csr_matrix(prepared_state.shape, dtype=complex)

        # print("prepared_state.type", type(prepared_state), "kraus_ops[0]", type(kraus_ops[0]))

        for kraus_op in kraus_ops:
            output_state += kraus_op @ prepared_state @ kraus_op.conj().T
        
        # print("output:", type(output_state))
        if verbose:
            print(output_state)
        self.set(all_keys, output_state)

    def add_loss(self, key, loss_rate, verbose = False):
        prepared_state, all_keys = self._prepare_state([key])
        local_kraus_ops = _build_amp_damping_kraus_operators(loss_rate, self.N)
        kraus_ops = [self._prepare_operator(all_keys, [key], op_subsystem) for op_subsystem in local_kraus_ops]
        self._apply_kraus_operators(prepared_state, all_keys, kraus_ops, verbose)


    def new(self, state=None) -> int:
        """Method to create a new state with key

        Args:
            state (Union[str, List[complex], List[List[complex]]]): amplitudes of new state.
                Default value is 'gnd': create zero-excitation state with current truncation.
                Other inputs are passed to the constructor of `DensityState`.
        """

        key = self._least_available
        self._least_available += 1
        if state is None:
            gnd = sp.csr_matrix((self.N**2, self.N**2))
            gnd[0,0] = 1
            self.states[key] = SparseDensityState(gnd, [key], truncation=self.truncation)
        else:
            self.states[key] = SparseDensityState(state, [key], truncation=self.truncation)

        return key
    
    def set(self, keys: List[int], state):
        # state_data = self.extract_sparse_data(state)
        new_state = SparseDensityState(state, keys, truncation=self.truncation)
        
        # print("size of dm while setting:", len(state.nonzero()[0]))
        if len(state.nonzero()[0]) > self.largest_dm_size:
            self.largest_dm_size = len(state.nonzero()[0])
        if len(state.nonzero()[0]) > self.largest_dm_dims:
            self.largest_dm_dims = state.shape[0]
        
        for key in keys:
            self.states[key] = new_state

    def _prepare_operator(self, all_keys: List[int], keys: List[int], operator):
        # pad operator with identity
        left_dim = self.dim ** all_keys.index(keys[0])
        right_dim = self.dim ** (len(all_keys) - all_keys.index(keys[-1]) - 1)
        prepared_operator = operator

        # print("befire prep op:", type(operator))

        if left_dim > 0:
            prepared_operator = sp.kron(sp.eye(left_dim), prepared_operator)
        if right_dim > 0:
            prepared_operator = sp.kron(prepared_operator, sp.eye(right_dim))

        # print("after prep op:", type(prepared_operator))
        return sp.csr_matrix(prepared_operator)

    def measure(self, keys: List[int], povms, sqrt_povms, meas_samp: float, outcome = None, measure_all=False, verbose = False) -> int:
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


        new_state, all_keys = self._prepare_state(keys)

        # if len(new_state.nonzero()[0]):
        #     self.largest_dm_size = len(new_state.nonzero()[0])

        new_state.data = np.round(new_state.data, 10)
        new_state.eliminate_zeros()

        # print("measuring:")
        # plt.figure()
        # plt.imshow(np.real(np.round(np.log(new_state.todense()))))
        # plt.title(f"measured state real {outcome}")
        # plt.figure()
        # plt.imshow(np.imag(np.round(np.log(new_state.todense()))))
        # plt.title(f"measured state imag {outcome}")

        # print("mat dim:", new_state.shape, "mat data:", len(new_state.data))
        if measure_all:
            return self._measure(new_state, all_keys, all_keys, povms, sqrt_povms, meas_samp, outcome = outcome, verbose = verbose)    
        return self._measure(new_state, keys, all_keys, povms, sqrt_povms, meas_samp, outcome = outcome, verbose = verbose)
    
    def _measure(self, state: List[List[complex]], keys: List[int],
                 all_keys: List[int], povm_tuple: tuple, sqrt_povm_tuple: tuple, meas_samp: float, outcome = None, verbose = False) -> int:
        """Method to measure subsystems at given keys in POVM formalism.

        Modifies quantum state of all qubits given by all_keys, post-measurement operator determined
        by measurement operators which are chosen as square root of POVM operators.

        Args:
            state (List[List[complex]]): state to measure.
            keys (List[int]): list of keys to measure.
            all_keys (List[int]): list of all keys corresponding to state.
            povms: (List[array]): list of POVM operators to use for measurement.
            meas_samp (float): random measurement sample to use for computing resultant state.

        Returns:
            int: measurement as index of matching POVM in supplied tuple.
        """
        # start = time.time()
        # print("state type is:", type(state))
        # print("povm type is:", type(povms[0]))
        # print("QM, POVM tuple", povm_tuple[1])

        state_tuple = self.extract_sparse_data(state) # tuple(map(tuple, state))
        # print("state tuple:", state_tuple)
        new_state = None
        result = 0

        if verbose:
            print("Input state tuple is:, len(keys)", len(keys))
            for i in state_tuple:
                print(' '.join(format(abs(f), '.2f') for f in i))

        # calculate meas probabilities and projected states
        if len(keys) == 1:
            if len(all_keys) == 1:
                states, probs = sparse_measure_state_with_cache_fock_density(state=state_tuple, povms=povm_tuple, sqrt_povms=sqrt_povm_tuple, basis_dim=self.dim)
                # print("probs:", probs)
            else:
                key = keys[0]
                len_all_keys = len(all_keys)
                key_index = all_keys.index(key)
                # print("state_index:", state_index)
                states, probs = \
                    sparse_measure_entangled_state_with_cache_fock_density(state=state_tuple, key_index=key_index, len_all_keys=len_all_keys, povms=povm_tuple, sqrt_povms=sqrt_povm_tuple, basis_dim=self.dim)
                # print("probs", probs)
        else:
            key_indices = tuple([all_keys.index(key) for key in keys])

            # This does not return a post measurement state for the sparse case. Moving into the POVM like measurements where post=-measurement state does not matter. 
            states, probs = \
                sparse_measure_multiple_with_cache_fock_density(state_tuple, key_indices, len(all_keys), povm_tuple,
                                                         basis_dim=self.dim)
            # print("expectd coincidenced prob:", probs[-1], "square of op:", probs[1])
            # print("state is:", state)
            if verbose: # verbose:
                print("probs:", probs)
                for state in states:
                    print("Possible next_state:")
                    try:
                        for i in state:
                            print(' '.join(format(abs(f), '.2f') for f in i))
                    except:
                        print(state)


        # Note that in the case when outcome is specified, you want the result returned from the function 
        # to be the probability of getting that output. Conversely, if you provide a random sample and expect to 
        # get a measurement result out randomly, you simply get the index of the measurement outcome and nothing else.  
        if states == None:
            return probs
        else: # what if you are finding the post measurement state. 
            new_state = None
            
            if outcome == None:
                prob_sum = cumsum(probs)
                for i, (output_state, p) in enumerate(zip(states, prob_sum)):
                    if meas_samp < p:
                        if states:
                            new_state = sp.csr_matrix(output_state)
                        result = i
                        break
            else: # If you have an expected outcome, this simply selects that outcome and saves the probability of that outcome. 
                result = np.round(probs[outcome], 15)
                # print("result:", result)
                # print("type(states[outcome])", type(states[outcome]))
                # print("outcome:", outcome)
                if not result == 0:
                    new_state = sp.csr_matrix(states[outcome])
                else:
                    new_state = None
            
             
        
        if not new_state == None: # This is equivalent to checking if we had an output state from the measurent state at all.
            for key in keys:
                self.states[key] = None  # clear the stored state at key (particle destructively measured)
            # assign remaining state
            if len(keys) < len(all_keys):
                key_indices = tuple([all_keys.index(key) for key in keys])
                new_state_tuple = self.extract_sparse_data(new_state)
                remaining_state = sparse_density_partial_trace(new_state_tuple, key_indices, len(all_keys), self.dim)
                remaining_keys = [key for key in all_keys if key not in keys]
                self.set(remaining_keys, remaining_state)


        if verbose:
            print("Actual result:")
            for i in remaining_state:
                print(' '.join(format(abs(f), '1.2e') for f in i))


        # print("time taken:", time.time() - start)
        return result