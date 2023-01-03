"""This module defines the quantum manager class, to track quantum states.

The states may currently be defined in two possible ways:
    - KetState (with the QuantumManagerKet class)
    - DensityMatrix (with the QuantumManagerDensity class)

The manager defines an API for interacting with quantum states.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..components.circuit import Circuit
    from .quantum_state import State

from qutip.qip.circuit import QubitCircuit, Gate
from qutip.qip.operations import gate_sequence_product
from numpy import log, array, cumsum, base_repr, zeros
from scipy.sparse import csr_matrix
from scipy.special import binom

from .quantum_state import KetState, DensityState
from .quantum_utils import *

KET_STATE_FORMALISM = "ket_vector"
DENSITY_MATRIX_FORMALISM = "density_matrix"
FOCK_DENSITY_MATRIX_FORMALISM = "fock_density"


class QuantumManager:
    """Class to track and manage quantum states (abstract).

    All states stored are of a single formalism (by default as a ket vector).

    Attributes:
        states (Dict[int, State]): mapping of state keys to quantum state objects.
        truncation (int): maximally allowed number of excited states for elementary subsystems.
                Default is 1 for qubit.
        dim (int): subsystem Hilbert space dimension. dim = truncation + 1
    """

    def __init__(self, formalism: str, truncation: int = 1):
        self.states: Dict[int, State] = {}
        self._least_available: int = 0
        self.formalism: str = formalism
        self.truncation = truncation
        self.dim = self.truncation + 1

    @abstractmethod
    def new(self, state: any) -> int:
        """Method to create a new quantum state.

        Args:
            state (any): complex amplitudes of new state. Type depends on type of subclass.

        Returns:
            int: key for new state generated.
        """
        pass

    def get(self, key: int) -> "State":
        """Method to get quantum state stored at an index.

        Args:
            key (int): key for quantum state.

        Returns:
            State: quantum state at supplied key.
        """
        return self.states[key]

    @abstractmethod
    def run_circuit(self, circuit: Circuit, keys: List[int], meas_samp=None) -> Dict[int, int]:
        """Method to run a circuit on a given set of quantum states.

        Args:
            circuit (Circuit): quantum circuit to apply.
            keys (List[int]): list of keys for quantum states to apply circuit to.
            meas_samp (float): random sample used for measurement.

        Returns:
            Dict[int, int]: dictionary mapping qstate keys to measurement results.
        """

        assert len(keys) == circuit.size, "mismatch between circuit size and supplied qubits"
        if len(circuit.measured_qubits) > 0:
            assert meas_samp, "must specify random sample when measuring qubits"

    def _prepare_circuit(self, circuit: Circuit, keys: List[int]):
        old_states = []
        all_keys = []

        # go through keys and get all unique qstate objects
        for key in keys:
            qstate = self.states[key]
            if qstate.keys[0] not in all_keys:
                old_states.append(qstate.state)
                all_keys += qstate.keys

        # construct compound state; order qubits
        new_state = [1]
        for state in old_states:
            new_state = kron(new_state, state)

        # get circuit matrix; expand if necessary
        circ_mat = circuit.get_unitary_matrix()
        if circuit.size < len(all_keys):
            # pad size of circuit matrix if necessary
            diff = len(all_keys) - circuit.size
            circ_mat = kron(circ_mat, identity(2 ** diff))

        # apply any necessary swaps
        if not all([all_keys.index(key) == i for i, key in enumerate(keys)]):
            all_keys, swap_mat = self._swap_qubits(all_keys, keys)
            circ_mat = circ_mat @ swap_mat

        return new_state, all_keys, circ_mat

    def _swap_qubits(self, all_keys, keys):
        swap_circuit = QubitCircuit(N=len(all_keys))
        for i, key in enumerate(keys):
            j = all_keys.index(key)
            if j != i:
                gate = Gate("SWAP", targets=[i, j])
                swap_circuit.add_gate(gate)
                all_keys[i], all_keys[j] = all_keys[j], all_keys[i]
        swap_mat = gate_sequence_product(swap_circuit.propagators()).full()
        return all_keys, swap_mat

    @abstractmethod
    def set(self, keys: List[int], amplitudes: any) -> None:
        """Method to set quantum state at a given key(s).

        Args:
            keys (List[int]): key(s) of state(s) to change.
            amplitudes (any): Amplitudes to set state to, type determined by type of subclass.
        """

        # num_subsystems = log(len(amplitudes)) / log(self.dim)
        # assert self.dim ** int(round(num_subsystems)) == len(amplitudes),\
        #     "Length of amplitudes should be d ** n, " \
        #     "where d is subsystem Hilbert space dimension and n is the number of subsystems. " \
        #     "Actual amplitude length: {}, dim: {}, num subsystems: {}".format(
        #         len(amplitudes), self.dim, num_subsystems
        #     )
        # num_subsystems = int(round(num_subsystems))
        # assert num_subsystems == len(keys),\
        #     "Length of amplitudes should be d ** n, " \
        #     "where d is subsystem Hilbert space dimension and n is the number of subsystems. " \
        #     "Amplitude length: {}, expected subsystems: {}, num keys: {}".format(
        #         len(amplitudes), num_subsystems, len(keys)
        #     )

        pass

    def remove(self, key: int) -> None:
        """Method to remove state stored at key."""
        del self.states[key]

    def set_states(self, states: Dict):
        self.states = states


class QuantumManagerKet(QuantumManager):
    """Class to track and manage quantum states with the ket vector formalism."""

    def __init__(self):
        super().__init__(KET_STATE_FORMALISM)

    def new(self, state=(complex(1), complex(0))) -> int:
        key = self._least_available
        self._least_available += 1
        self.states[key] = KetState(state, [key])
        return key

    def run_circuit(self, circuit: Circuit, keys: List[int], meas_samp=None) -> Dict[int, int]:
        super().run_circuit(circuit, keys, meas_samp)
        new_state, all_keys, circ_mat = self._prepare_circuit(circuit, keys)

        new_state = circ_mat @ new_state

        if len(circuit.measured_qubits) == 0:
            # set state, return no measurement result
            new_ket = KetState(new_state, all_keys)
            for key in all_keys:
                self.states[key] = new_ket
            return {}
        else:
            # measure state (state reassignment done in _measure method)
            keys = [all_keys[i] for i in circuit.measured_qubits]
            return self._measure(new_state, keys, all_keys, meas_samp)

    def set(self, keys: List[int], amplitudes: List[complex]) -> None:
        super().set(keys, amplitudes)
        new_state = KetState(amplitudes, keys)
        for key in keys:
            self.states[key] = new_state

    def set_to_zero(self, key: int):
        self.set([key], [complex(1), complex(0)])

    def set_to_one(self, key: int):
        self.set([key], [complex(0), complex(1)])

    def _measure(self, state: List[complex], keys: List[int],
                 all_keys: List[int], meas_samp: float) -> Dict[int, int]:
        """Method to measure qubits at given keys.

        SHOULD NOT be called individually; only from circuit method (unless for unit testing purposes).
        Modifies quantum state of all qubits given by all_keys.

        Args:
            state (List[complex]): state to measure.
            keys (List[int]): list of keys to measure.
            all_keys (List[int]): list of all keys corresponding to state.
            meas_samp (float): random sample used for measurement result.

        Returns:
            Dict[int, int]: mapping of measured keys to measurement results.
        """

        if len(keys) == 1:
            if len(all_keys) == 1:
                prob_0 = measure_state_with_cache_ket(tuple(state))
                if meas_samp < prob_0:
                    result = 0
                else:
                    result = 1

            else:
                key = keys[0]
                num_states = len(all_keys)
                state_index = all_keys.index(key)
                state_0, state_1, prob_0 = measure_entangled_state_with_cache_ket(tuple(state), state_index, num_states)
                if meas_samp < prob_0:
                    new_state = array(state_0, dtype=complex)
                    result = 0
                else:
                    new_state = array(state_1, dtype=complex)
                    result = 1

            all_keys.remove(keys[0])

        else:
            # swap states into correct position
            if not all(
                    [all_keys.index(key) == i for i, key in enumerate(keys)]):
                all_keys, swap_mat = self._swap_qubits(all_keys, keys)
                state = swap_mat @ state

            # calculate meas probabilities and projected states
            len_diff = len(all_keys) - len(keys)
            new_states, probabilities = measure_multiple_with_cache_ket(
                tuple(state), len(keys), len_diff)

            # choose result, set as new state
            for i in range(int(2 ** len(keys))):
                if meas_samp < sum(probabilities[:i + 1]):
                    result = i
                    new_state = new_states[i]
                    break

            for key in keys:
                all_keys.remove(key)

        result_states = [array([1, 0]), array([0, 1])]
        result_digits = [int(x) for x in bin(result)[2:]]
        while len(result_digits) < len(keys):
            result_digits.insert(0, 0)

        for res, key in zip(result_digits, keys):
            # set to state measured
            new_state_obj = KetState(result_states[res], [key])
            self.states[key] = new_state_obj
        
        if len(all_keys) > 0:
            new_state_obj = KetState(new_state, all_keys)
            for key in all_keys:
                self.states[key] = new_state_obj
        
        return dict(zip(keys, result_digits))


class QuantumManagerDensity(QuantumManager):
    """Class to track and manage states with the density matrix formalism."""

    def __init__(self):
        super().__init__(DENSITY_MATRIX_FORMALISM)

    def new(self,
            state=([complex(1), complex(0)], [complex(0), complex(0)])) -> int:
        key = self._least_available
        self._least_available += 1
        self.states[key] = DensityState(state, [key])
        return key

    def run_circuit(self, circuit: Circuit, keys: List[int], meas_samp=None) -> Dict[int, int]:
        super().run_circuit(circuit, keys, meas_samp)
        new_state, all_keys, circ_mat = super()._prepare_circuit(circuit, keys)

        new_state = circ_mat @ new_state @ circ_mat.conj().T

        if len(circuit.measured_qubits) == 0:
            # set state, return no measurement result
            new_state_obj = DensityState(new_state, all_keys)
            for key in all_keys:
                self.states[key] = new_state_obj
            return {}
        else:
            # measure state (state reassignment done in _measure method)
            keys = [all_keys[i] for i in circuit.measured_qubits]
            return self._measure(new_state, keys, all_keys, meas_samp)

    def set(self, keys: List[int], state: List[List[complex]]) -> None:
        """Method to set the quantum state at the given keys.

        The `state` argument should be passed as List[List[complex]], where each internal list is a row.
        However, the `state` may also be given as a one-dimensional pure state.
        If the list is one-dimensional, will be converted to matrix with the outer product operation.

        Args:
            keys (List[int]): list of quantum manager keys to modify.
            state: quantum state to set input keys to.
        """

        super().set(keys, state)
        new_state = DensityState(state, keys)
        for key in keys:
            self.states[key] = new_state

    def set_to_zero(self, key: int):
        self.set([key], [[complex(1), complex(0)], [complex(0), complex(0)]])

    def set_to_one(self, key: int):
        self.set([key], [[complex(0), complex(0)], [complex(0), complex(1)]])

    def _measure(self, state: List[List[complex]], keys: List[int],
                 all_keys: List[int], meas_samp: float) -> Dict[int, int]:
        """Method to measure qubits at given keys.

        SHOULD NOT be called individually; only from circuit method (unless for unit testing purposes).
        Modifies quantum state of all qubits given by all_keys.

        Args:
            state (List[complex]): state to measure.
            keys (List[int]): list of keys to measure.
            all_keys (List[int]): list of all keys corresponding to state.
            meas_samp (float): random sample used for measurement result.

        Returns:
            Dict[int, int]: mapping of measured keys to measurement results.
        """

        if len(keys) == 1:
            if len(all_keys) == 1:
                prob_0 = measure_state_with_cache_density(tuple(map(tuple, state)))
                if meas_samp < prob_0:
                    result = 0
                    new_state = [[1, 0], [0, 0]]
                else:
                    result = 1
                    new_state = [[0, 0], [0, 1]]

            else:
                key = keys[0]
                num_states = len(all_keys)
                state_index = all_keys.index(key)
                state_0, state_1, prob_0 =\
                    measure_entangled_state_with_cache_density(tuple(map(tuple, state)), state_index, num_states)
                if meas_samp < prob_0:
                    new_state = array(state_0, dtype=complex)
                    result = 0
                else:
                    new_state = array(state_1, dtype=complex)
                    result = 1

        else:
            # swap states into correct position
            if not all(
                    [all_keys.index(key) == i for i, key in enumerate(keys)]):
                all_keys, swap_mat = self._swap_qubits(all_keys, keys)
                state = swap_mat @ state @ swap_mat.T

            # calculate meas probabilities and projected states
            len_diff = len(all_keys) - len(keys)
            state_to_measure = tuple(map(tuple, state))
            new_states, probabilities = measure_multiple_with_cache_density(
                state_to_measure, len(keys), len_diff)

            # choose result, set as new state
            for i in range(int(2 ** len(keys))):
                if meas_samp < sum(probabilities[:i + 1]):
                    result = i
                    new_state = new_states[i]
                    break

        result_digits = [int(x) for x in bin(result)[2:]]
        while len(result_digits) < len(keys):
            result_digits.insert(0, 0)

        new_state_obj = DensityState(new_state, all_keys)
        for key in all_keys:
            self.states[key] = new_state_obj

        return dict(zip(keys, result_digits))


class QuantumManagerDensityFock(QuantumManager):
    """Class to track and manage Fock states with the density matrix formalism."""

    def __init__(self, truncation: int = 1):
        # default truncation is 1 for 2-d Fock space.
        super().__init__(DENSITY_MATRIX_FORMALISM, truncation=truncation)

    def new(self, state='gnd') -> int:
        """Method to create a new state with key

        Args:
            state (Union[str, List[complex], List[List[complex]]]): amplitudes of new state.
                Default value is 'gnd': create zero-excitation state with current truncation.
                Other inputs are passed to the constructor of `DensityState`.
        """

        key = self._least_available
        self._least_available += 1
        if state == 'gnd':
            gnd = [1] + [0]*self.truncation
            self.states[key] = DensityState(gnd, [key], truncation=self.truncation)
        else:
            self.states[key] = DensityState(state, [key], truncation=self.truncation)

        return key

    def run_circuit(self, circuit: Circuit, keys: List[int], meas_samp=None) -> Dict[int, int]:
        """Currently the Fock states do not support quantum circuits.
        This method is only to implement abstract method of parent class and SHOULD NOT be called after instantiation.
        """
        raise Exception("run_circuit method of class QuantumManagerDensityFock called")

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
            new_str = ''.join((old_str[:i], old_str[j], old_str[i+1:j], old_str[i], old_str[j+1:]))
            new_index = int(new_str, base=self.dim)
            swap_unitary[new_index, old_index] = 1

        return swap_unitary

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

    def _prepare_operator(self, all_keys: List[int], keys: List[int], operator) -> array:
        # pad operator with identity
        left_dim = self.dim ** all_keys.index(keys[0])
        right_dim = self.dim ** (len(all_keys) - all_keys.index(keys[-1]) - 1)
        prepared_operator = operator

        if left_dim > 0:
            prepared_operator = kron(identity(left_dim), prepared_operator)
        if right_dim > 0:
            prepared_operator = kron(prepared_operator, identity(right_dim))

        return prepared_operator

    def apply_operator(self, operator: array, keys: List[int]):
        prepared_state, all_keys = self._prepare_state(keys)
        prepared_operator = self._prepare_operator(all_keys, keys, operator)
        new_state = prepared_operator @ prepared_state @ prepared_operator.conj().T
        self.set(all_keys, new_state)

    def set(self, keys: List[int], state: List[List[complex]]) -> None:
        """Method to set the quantum state at the given keys.

        The `state` argument should be passed as List[List[complex]], where each internal list is a row.
        However, the `state` may also be given as a one-dimensional pure state.
        If the list is one-dimensional, will be converted to matrix with the outer product operation.

        Args:
            keys (List[int]): list of quantum manager keys to modify.
            state: quantum state to set input keys to.
        """

        super().set(keys, state)
        new_state = DensityState(state, keys, truncation=self.truncation)
        for key in keys:
            self.states[key] = new_state

    def set_to_zero(self, key: int):
        """set the state to ground (zero) state."""
        gnd = [1] + [0]*self.truncation
        self.set([key], gnd)

    def build_ladder(self):
        """Generate matrix of creation and annihilation (ladder) operators on truncated Hilbert space."""
        truncation = self.truncation
        data = array([sqrt(i+1) for i in range(truncation)])  # elements in create/annihilation operator matrix
        row = array([i+1 for i in range(truncation)])
        col = array([i for i in range(truncation)])
        create = csr_matrix((data, (row, col)), shape=(truncation+1, truncation+1)).toarray()
        destroy = create.conj().T

        return create, destroy

    def measure(self, keys: List[int], povms: List[array], meas_samp: float) -> int:
        """Method to measure subsystems at given keys in POVM formalism.

        Serves as wrapper for private `_measure` method, performing quantum manager specific operations.

        Args:
            keys (List[int]): list of keys to measure.
            povms: (List[array]): list of POVM operators to use for measurement.
            meas_samp (float): random measurement sample to use for computing resultant state.

        Returns:
            int: measurement as index of matching POVM in supplied tuple.
        """

        new_state, all_keys = self._prepare_state(keys)
        return self._measure(new_state, keys, all_keys, povms, meas_samp)

    def _measure(self, state: List[List[complex]], keys: List[int],
                 all_keys: List[int], povms: List[array], meas_samp: float) -> int:
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
                states, probs = \
                    measure_entangled_state_with_cache_fock_density(state_tuple, state_index, num_states, povm_tuple,
                                                                    self.truncation)

        else:
            indices = tuple([all_keys.index(key) for key in keys])
            states, probs = \
                measure_multiple_with_cache_fock_density(state_tuple, indices, len(all_keys), povm_tuple,
                                                         self.truncation)

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

    def _build_loss_kraus_operators(self, loss_rate: float, all_keys: List[int], key: int) -> List[array]:
        """Method to build Kraus operators of a generalized amplitude damping channel.

        This represents the effect of photon loss.

        Args:
            loss_rate (float): loss rate for the quantum channel.
            all_keys (List[int]): list of all keys in affected state.
            key (int): key for subsystem experiencing loss.

        Returns:
            List[array]: list of generated Kraus operators.
        """

        assert 0 <= loss_rate <= 1
        kraus_ops = []

        for k in range(self.dim):
            total_kraus_op = zeros((self.dim ** len(all_keys), self.dim ** len(all_keys)))

            for n in range(k, self.dim):
                coeff = sqrt(binom(n, k)) * sqrt(((1-loss_rate) ** (n-k)) * (loss_rate ** k))
                single_op = zeros((self.dim, self.dim))
                single_op[n-k, n] = 1
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
