"""
This module implements the quantum manager for Fock states with the density matrix formalism.
"""

from math import sqrt
from numpy import array, base_repr, cumsum, identity, kron, zeros
from numpy.typing import NDArray
from scipy.sparse import csr_matrix
from scipy.special import binom

from .base import QuantumManager
from ..quantum_state import DensityState
from ..quantum_utils import (density_partial_trace, measure_entangled_state_with_cache_fock_density, 
                             measure_multiple_with_cache_fock_density, measure_state_with_cache_fock_density)
from ...constants import FOCK_DENSITY_MATRIX_FORMALISM


@QuantumManager.register(FOCK_DENSITY_MATRIX_FORMALISM)
class QuantumManagerDensityFock(QuantumManager):
    """Class to track and manage Fock states with the density matrix formalism.
    
    Attributes:
        truncation (int): maximally allowed number of excited states for elementary subsystems. Default is 1 for qubit.
        dim (int): subsystem Hilbert space dimension. dim = truncation + 1
    """

    def __init__(self, truncation: int = 1):
        super().__init__()
        self.truncation = truncation
        self.dim = self.truncation + 1

    def new(self, state=None) -> int:
        """Method to create a new state with key

        Args:
            state (str | list[complex] | list[list[complex]]): amplitudes of new state.
                Default value is 'gnd': create zero-excitation state with current truncation.
                Other inputs are passed to the constructor of `DensityState`.
        """

        key = self._least_available
        self._least_available += 1
        if state is None:
            gnd = [1] + [0] * self.truncation
            self.states[key] = DensityState(gnd, [key], truncation=self.truncation)
        else:
            self.states[key] = DensityState(state, [key], truncation=self.truncation)

        return key

    def _generate_swap_operator(self, num_systems: int, i: int, j: int):
        """Helper function to generate swapping unitary.

        Args:
            num_systems (int): number of subsystems in state
            i (int): index of first subsystem to swap
            j (int): index of second subsystem to swap

        Returns:
            Array[int]: unitary swapping operator
        """

        size = self.dim ** num_systems
        swap_unitary = zeros((size, size))

        for old_index in range(size):
            old_str = base_repr(old_index, self.dim)
            old_str = old_str.zfill(num_systems)
            new_str = ''.join((old_str[:i], old_str[j], old_str[i + 1:j], old_str[i], old_str[j + 1:]))
            new_index = int(new_str, base=self.dim)
            swap_unitary[new_index, old_index] = 1

        return swap_unitary

    def _prepare_state(self, keys: list[int]):
        """Function to prepare states at given keys for operator application.

        Will take composite quantum state and swap subsystems to correspond with listed keys.
        Should not be called directly, but from method to apply operator or measure state.

        Args:
            keys (list[int]): keys for states to apply operator to.

        Returns:
            tuple(list[list[complex]], list[int]): tuple containing:
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
        new_state = [1]
        for state in old_states:
            new_state = kron(new_state, state)

        # apply any necessary swaps to order keys
        if len(keys) > 1:

            # generate desired key order
            start_idx = all_keys.index(keys[0])
            if start_idx + len(keys) > len(all_keys):
                start_idx = len(all_keys) - len(keys)

            for i, key in enumerate(keys):
                i = i + start_idx
                j = all_keys.index(key)
                if j != i:
                    swap_unitary = self._generate_swap_operator(len(all_keys), i, j)
                    new_state = swap_unitary @ new_state @ swap_unitary.T
                    all_keys[i], all_keys[j] = all_keys[j], all_keys[i]

        return new_state, all_keys

    def _prepare_operator(self, all_keys: list[int], keys: list[int], operator) -> NDArray:
        # pad operator with identity
        left_dim = self.dim ** all_keys.index(keys[0])
        right_dim = self.dim ** (len(all_keys) - all_keys.index(keys[-1]) - 1)
        prepared_operator = operator

        if left_dim > 0:
            prepared_operator = kron(identity(left_dim), prepared_operator)
        if right_dim > 0:
            prepared_operator = kron(prepared_operator, identity(right_dim))

        return prepared_operator

    def apply_operator(self, operator: NDArray, keys: list[int]):
        prepared_state, all_keys = self._prepare_state(keys)
        prepared_operator = self._prepare_operator(all_keys, keys, operator)
        new_state = prepared_operator @ prepared_state @ prepared_operator.conj().T
        self.set(all_keys, new_state)

    def set(self, keys: list[int], state: list[list[complex]]) -> None:
        """Method to set the quantum state at the given keys.

        The `state` argument should be passed as list[list[complex]], where each internal list is a row.
        However, the `state` may also be given as a one-dimensional pure state.
        If the list is one-dimensional, will be converted to matrix with the outer product operation.

        Args:
            keys (list[int]): list of quantum manager keys to modify.
            state: quantum state to set input keys to.
        """
        new_state = DensityState(state, keys, truncation=self.truncation)
        for key in keys:
            self.states[key] = new_state

    def set_to_zero(self, key: int):
        """set the state to ground (zero) state.
        
        Args:
            key (int): key of the state to set to ground state.
        """
        gnd = [1] + [0] * self.truncation
        self.set([key], gnd)

    def build_ladder(self):
        """Generate matrix of creation and annihilation (ladder) operators on truncated Hilbert space."""
        truncation = self.truncation
        data = array([sqrt(i + 1) for i in range(truncation)])  # elements in create/annihilation operator matrix
        row = array([i + 1 for i in range(truncation)])
        col = array([i for i in range(truncation)])
        create = csr_matrix((data, (row, col)), shape=(truncation + 1, truncation + 1)).toarray()
        destroy = create.conj().T

        return create, destroy

    def measure(self, keys: list[int], povms: list[NDArray], meas_samp: float) -> int:
        """Method to measure subsystems at given keys in POVM formalism.

        Serves as wrapper for private `_measure` method, performing quantum manager specific operations.

        Args:
            keys (list[int]): list of keys to measure.
            povms: (list[array]): list of POVM operators to use for measurement.
            meas_samp (float): random measurement sample to use for computing resultant state.

        Returns:
            int: measurement as index of matching POVM in supplied tuple.
        """

        new_state, all_keys = self._prepare_state(keys)
        return self._measure(new_state, keys, all_keys, povms, meas_samp)

    def _measure(self, state: list[list[complex]], keys: list[int],
                 all_keys: list[int], povms: list[NDArray], meas_samp: float) -> int:
        """Method to measure subsystems at given keys in POVM formalism.

        Modifies quantum state of all qubits given by all_keys, post-measurement operator determined
        by measurement operators which are chosen as square root of POVM operators.

        Args:
            state (list[list[complex]]): state to measure.
            keys (list[int]): list of keys to measure.
            all_keys (list[int]): list of all keys corresponding to state.
            povms: (list[NDArray]): list of POVM operators to use for measurement.
            meas_samp (float): random measurement sample to use for computing resultant state.

        Returns:
            int: measurement as index of matching POVM in supplied tuple.
        """

        state_tuple = tuple(map(tuple, state))
        povm_tuple = tuple([tuple(map(tuple, povm)) for povm in povms])
        new_state = None
        result = 0

        # calculate meas probabilities and projected states
        if len(keys) == 1:
            if len(all_keys) == 1:
                states, probs = measure_state_with_cache_fock_density(state_tuple, povm_tuple)

            else:
                key = keys[0]
                num_states = len(all_keys)
                state_index = all_keys.index(key)
                states, probs = measure_entangled_state_with_cache_fock_density(state_tuple, state_index, num_states, 
                                                                                povm_tuple, self.truncation)

        else:
            indices = tuple([all_keys.index(key) for key in keys])
            states, probs = measure_multiple_with_cache_fock_density(state_tuple, indices, len(all_keys), 
                                                                     povm_tuple, self.truncation)

        # calculate result based on measurement sample.
        prob_sum = cumsum(probs)
        for i, (output_state, p) in enumerate(zip(states, prob_sum)):
            if meas_samp < p:
                new_state = output_state
                result = i
                break

        """
        # for potential future work
        result_digits = [int(x) for x in base_repr(result, base=self.dim)[2:]]
        while len(result_digits) < len(keys):
            result_digits.insert(0, 0)

        # assign measured states
        for key, result in zip(keys, result_digits):
            state = [0] * self.dim
            state[result] = 1
            self.set([key], state)
        """

        for key in keys:
            self.states[key] = None  # clear the stored state at key (particle destructively measured)

        # assign remaining state
        if len(keys) < len(all_keys):
            indices = tuple([all_keys.index(key) for key in keys])
            new_state_tuple = tuple(map(tuple, new_state))
            remaining_state = density_partial_trace(new_state_tuple, indices, len(all_keys), self.truncation)
            remaining_keys = [key for key in all_keys if key not in keys]
            self.set(remaining_keys, remaining_state)

        return result

    def _build_loss_kraus_operators(self, loss_rate: float, all_keys: list[int], key: int) -> list[array]:
        """Method to build Kraus operators of a generalized amplitude damping channel.

        This represents the effect of photon loss.

        Args:
            loss_rate (float): loss rate for the quantum channel.
            all_keys (list[int]): list of all keys in affected state.
            key (int): key for subsystem experiencing loss.

        Returns:
            list[array]: list of generated Kraus operators.
        """

        assert 0 <= loss_rate <= 1
        kraus_ops = []

        for k in range(self.dim):
            total_kraus_op = zeros((self.dim ** len(all_keys), self.dim ** len(all_keys)))

            for n in range(k, self.dim):
                coeff = sqrt(binom(n, k)) * sqrt(((1 - loss_rate) ** (n - k)) * (loss_rate ** k))
                single_op = zeros((self.dim, self.dim))
                single_op[n - k, n] = 1
                total_op = self._prepare_operator(all_keys, [key], single_op)
                total_kraus_op += coeff * total_op

            kraus_ops.append(total_kraus_op)

        return kraus_ops

    def add_loss(self, key, loss_rate):
        """Method to apply generalized amplitude damping channel on a *single* subspace corresponding to `key`.

        Args:
            key (int): key for the subspace experiencing loss.
            loss_rate (float): loss rate for the quantum channel.
        """

        prepared_state, all_keys = self._prepare_state([key])
        kraus_ops = self._build_loss_kraus_operators(loss_rate, all_keys, key)
        output_state = zeros(prepared_state.shape, dtype=complex)

        for kraus_op in kraus_ops:
            output_state += kraus_op @ prepared_state @ kraus_op.conj().T

        self.set(all_keys, output_state)
