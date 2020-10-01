from copy import copy
from qutip.qip.circuit import QubitCircuit, Gate
from qutip.qip.operations import gate_sequence_product
from numpy import log2, array, kron, identity
from typing import List, Tuple, TYPE_CHECKING


class QuantumManager():
    """Class to track and manage quantum states.

    All states stored are of a single formalism (by default as a ket vector).

    Attributes:
        states (Dict[int, KetState]): mapping of state keys to quantum state objects.
    """

    def __init__(self):
        self.states = {}
        self._least_available = 0

    def new(self, amplitudes=[complex(1), complex(0)]) -> int:
        """Method to create a new quantum state.

        Args:
            amplitudes (List[complex]): complex amplitudes of new state (default [1, 0]).

        Returns:
            int: key for new state generated.
        """
        
        key = self._least_available
        self._least_available += 1
        self.states[key] = KetState(amplitudes, [key])
        return key

    def get(self, key: int) -> "KetState":
        """Method to get quantum state stored at an index.

        Args:
            key (int): key for quantum state.

        Returns:
            KetState: quantum state at supplied key.
        """
        return self.states[key]

    def run_circuit(self, circuit: "Circuit", keys: List[int]) -> List[int]:
        """Method to run a circuit on a given set of quantum states.
        
        Args:
            circuit (Circuit): quantum circuit to apply.
            keys (List[int]): list of keys for quantum states to apply circuit to.

        Returns:
            Tuple[int]: measurement results.
        """
        assert len(keys) == circuit.size, "mismatch between circuit size and supplied qubits"

        old_states = []
        all_keys = []
        for key in keys:
            qstate = self.states[key]
            if qstate.keys[0] not in all_keys:
                old_states.append(qstate.state)
                all_keys += qstate.keys

        # construct compound state; order qubits
        new_state = [1]
        for state in old_states:
            new_state = kron(new_state, state)

        if not all([all_keys.index(key) == i for i, key in enumerate(keys)]):
            print("got here")
            print(all_keys)
            swap_circuit = QubitCircuit(N=len(all_keys))
            for i, key in enumerate(keys):
                j = all_keys.index(key)
                if j != i:
                    gate = Gate("SWAP", targets=[i, j])
                    swap_circuit.add_gate(gate)
                    all_keys[i], all_keys[j] = all_keys[j], all_keys[i]
            swap_mat = gate_sequence_product(swap_circuit.propagators())
            new_state = swap_mat @ new_state
            print(all_keys)
        
        # multiply circuit matrix
        circ_mat = circuit.get_unitary_matrix()
        if circuit.size < len(all_keys):
            # pad size of circuit matrix if necessary
            diff = len(all_keys) - circuit.size
            circ_mat = circ_mat @ identity(diff)
        new_state = circ_mat @ new_state

        # measure (TODO)

        # set state, return
        for key in all_keys:
            self.states[key] = KetState(new_state, all_keys)
        return None

    def set(self, keys: List[int], amplitudes: List[complex]) -> None:
        """Method to set quantum state at a given key(s).

        Args:
            keys (List[int]): key(s) of state(s) to change.
            amplitudes (List[complex]): List of amplitudes to set state to (should be of length 2 ** len(keys)).
        """

        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of keys"
        num_qubits = int(num_qubits)
        assert num_qubits == len(keys), "Length of amplitudes should be 2 ** n, where n is the number of keys"

        new_state = KetState(amplitudes, keys)
        for key in keys:
            self.states[key] = new_state

    def remove(self, key: int) -> None:
        """Method to remove state stored at key."""
        del self.states[key]


class KetState():
    def __init__(self, amplitudes: List[complex], keys: List[int]):
        # check formatting
        assert all([abs(a) <= 1 for a in amplitudes]), "Illegal value with abs>1 in ket vector"
        assert abs(sum([a ** 2 for a in amplitudes]) - 1) < 1e-5, "Squared amplitudes do not sum to 1" 
        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer(), "Length of amplitudes should be 2 ** n, where n is the number of qubits"
        assert num_qubits == len(keys), "Length of amplitudes should be 2 ** n, where n is the number of qubits"

        self.state = array(amplitudes)
        self.keys = keys

