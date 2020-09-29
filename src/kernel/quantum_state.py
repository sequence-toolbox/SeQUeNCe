from numpy import log2, array
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

        pass

    def set(self, keys: List[int], amplitudes: List[complex]) -> None:
        """Method to set quantum state at a given key(s).

        Args:
            keys (List[int]): key(s) of state(s) to change.
            amplitudes (List[complex]): List of amplitudes to set state to (should be of length 2 ** len(keys)).
        """

        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer()
        num_qubits = int(num_qubits)
        assert num_qubits == len(keys)

        new_state = KetState(amplitudes, keys)
        for key in keys:
            self.states[key] = new_state

    def remove(self, key: int) -> None:
        """Method to remove state stored at key."""
        del self.states[key]


class KetState():
    def __init__(self, amplitudes: List[complex], keys: List[int]):
        # check formatting
        assert all([abs(a) <= 1 for a in amplitudes])
        num_qubits = log2(len(amplitudes))
        assert num_qubits.is_integer()
        assert num_qubits == len(keys)

        self.state = array(amplitudes)
        self.keys = keys

