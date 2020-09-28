"""Models for simulation of quantum circuit

This module introduces the QuantumCircuit class.
"""
from typing import List, TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .memory import Memory


class Circuit():
    """Class of quantum circuit

    Attributes:
        size (int): the number of quantum qubits of circuit
        gates (List[str]): a list of command bound to some registers
        circuit_matrix (List[List[complex]]): the unitary matrix of circuit
    """

    def __init__(self, size: int):
        self.size = size
        self.gates = []
        self.circuit_matrix = None

    def h(self, qubit: int):
        """Method to apply single-qubit Hadamard gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def x(self, qubit: int):
        """Method to apply single-qubit Pauli-X gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def y(self, qubit: int):
        """Method to apply single-qubit Pauli-Y gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def z(self, qubit: int):
        """Method to apply single-qubit Pauli-Z gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def cx(self, control: int, target: int):
        """Method to apply Control-X gate on three qubits.

        Args:
            control1 (int): the index of control1 in the circuit
            target (int): the index of target in the circuit

        """
        pass

    def ccx(self, control1: int, control2: int, target: int):
        """Method to apply Toffoli gate on three qubits.

        Args:
            control1 (int): the index of control1 in the circuit
            control2 (int): the index of control2 in the circuit
            target (int): the index of target in the circuit

        """
        pass

    def swap(self, qubit1: int, qubit2: int):
        """Method to apply SWAP gate on two qubits.

        Args:
            qubit1 (int): the index of qubit1 in the circuit
            qubit2 (int): the index of qubit2 in the circuit

        """
        pass

    def t(self, qubit: int):
        """Method to apply single T gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def s(self, qubit: int):
        """Method to apply single S gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def measure(self, qubit: int):
        """Method to measure quantum bit into classical bit.

        Args:
            qubit (int): the index of qubit in the circuit

        """
        pass

    def run(self, input: List["Memory"]) -> Dict[int:int]:
        """Method to run circuit based on the given qubits

        Returns:
            Dict[int:int]: the measurement result of i-th qubit
        """
        pass

    def __str__(self) -> str:
        pass
