"""This module defines the quantum manager class, to track quantum states.

The states may currently be defined in two possible ways:
    - KetState (with the QuantumManagerKet class)
    - DensityMatrix (with the QuantumManagerDensity class)

The manager defines an API for interacting with quantum states.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import List, Dict, TYPE_CHECKING

from qutip.qip.circuit import QubitCircuit, Gate
from qutip.qip.operations import gate_sequence_product
from numpy import log2, outer

from .quantum_utils import *

if TYPE_CHECKING:
    from ..components.circuit import Circuit

KET_STATE_FORMALISM = "ket_vector"
DENSITY_MATRIX_FORMALISM = "density_matrix"


class QuantumManager():
    """Class to track and manage quantum states (abstract).

    All states stored are of a single formalism (by default as a ket vector).

    Attributes:
        states (Dict[int, State]): mapping of state keys to quantum state objects.
        formalism (str): formalism used for local quantum state representation.
    """

    def __init__(self, formalism: str):
        self.states: Dict[int, State] = {}
        self._least_available: int = 0
        self.formalism: str = formalism

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
    def run_circuit(self, circuit: Circuit, keys: List[int],
                    meas_samp=None) -> int:
        """Method to run a circuit on a given set of quantum states.

        Args:
            circuit (Circuit): quantum circuit to apply.
            keys (List[int]): list of keys for quantum states to apply circuit to.
            meas_samp (float): random sample used for measurement.

        Returns:
            Dict[int, int]: dictionary mapping qstate keys to measurement results.
        """

        assert len(
            keys) == circuit.size, "mismatch between circuit size and supplied qubits"
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

        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of keys"
        num_qubits = int(num_qubits)
        assert num_qubits == len(
            keys), "Length of amplitudes should be 2 ** n, where n is the number of keys"

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

    def run_circuit(self, circuit: Circuit, keys: List[int],
                    meas_samp=None) -> Dict[int, int]:
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

    def run_circuit(self, circuit: Circuit, keys: List[int],
                    meas_samp=None) -> Dict[int, int]:
        super().run_circuit(circuit, keys, meas_samp)
        new_state, all_keys, circ_mat = super()._prepare_circuit(circuit, keys)

        new_state = circ_mat @ new_state @ circ_mat.T

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
                state_0, state_1, prob_0 = measure_entangled_state_with_cache_density(tuple(map(tuple, state)),
                        state_index, num_states)
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


class State():
    """Class to represent state of qubits.

    Attributes:
        state (any): internal representation of qubit state. Varies based on formalism.
        keys (list[int]): associated keys for a quantum manager.
    """

    def __init__(self, state, keys):
        self.state = state
        self.keys = keys

    def __str__(self):
        return "\n".join(["Keys:", str(self.keys), "State:", str(self.state)])

    def deserialize(self, json_data) -> None:
        self.keys = json_data["keys"]
        self.state = []
        for i in range(0, len(json_data["state"]), 2):
            complex_val = complex(json_data["state"][i],
                                  json_data["state"][i + 1])
            self.state.append(complex_val)

    def serialize(self) -> Dict:
        res = {"keys": self.keys}
        state = []
        for cplx_n in self.state:
            if type(cplx_n) == float:
                state.append(cplx_n)
                state.append(0)
            elif isinstance(cplx_n, complex):
                state.append(cplx_n.real)
                state.append(cplx_n.imag)
            else:
                assert "Unknow type of state"

        res["state"] = state
        return res


class KetState(State):
    """Class inheriting State class to represent an individual quantum state
    as a ket vector.

    Attributes:
        state (np.array): state vector. Should be of length 2 ** len(keys).
        keys (List[int]): list of keys (qubits) associated with this state.
    """

    def __init__(self, amplitudes: List[complex], keys: List[int]):
        # check formatting
        assert all([abs(a) <= 1.01 for a in
                    amplitudes]), "Illegal value with abs > 1 in ket vector"
        assert abs(sum([a ** 2 for a in
                        amplitudes]) - 1) < 1e-5, "Squared amplitudes do not sum to 1"
        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of qubits"
        assert num_qubits == len(
            keys), "Length of amplitudes should be 2 ** n, where n is the number of qubits"
        super().__init__(array(amplitudes, dtype=complex), keys)


class DensityState(State):
    """Class inheriting State class to represent an individual quantum state
    as a density matrix.

    Attributes:
        state (np.array): density matrix values. NxN matrix with N = 2 ** len(keys).
        keys (List[int]): list of keys (qubits) associated with this state.
    """

    def __init__(self, state: List[List[complex]], keys: List[int]):
        """Constructor for density state class.

        Args:
            state (List[List[complex]]): density matrix elements given as a
                list. If the list is one-dimensional, will be converted to
                matrix with the outer product operation.
            keys (List[int]): list of keys to this state in quantum manager.
        """

        state = array(state, dtype=complex)
        if state.ndim == 1:
            state = outer(state.conj(), state)

        # check formatting
        assert abs(trace(array(state)) - 1) < 0.1, "density matrix trace must be 1"
        for row in state:
            assert len(state) == len(row), "density matrix must be square"
        num_qubits = log2(len(state))
        assert num_qubits.is_integer(), "Dimensions of density matrix should be 2 ** n, where n is the number of qubits"
        assert num_qubits == len(keys), "Dimensions of density matrix should be 2 ** n, where n is the number of qubits"
        super().__init__(state, keys)
