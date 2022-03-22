"""Models for simulation of quantum circuit.

This module introduces the QuantumCircuit class. The qutip library is used to calculate the unitary matrix of a circuit.
"""

from math import e, pi
from typing import List, Dict, Union, Optional

import numpy as np
from qutip.qip.circuit import QubitCircuit
from qutip.qip.operations import gate_sequence_product
from qutip import Qobj

GATE_INFO_TYPE = List[Union[str, List[int], float]]


def x_gate():
    mat = np.array([[0, 1],
                    [1, 0]])
    return Qobj(mat, dims=[[2], [2]])


def y_gate():
    mat = np.array([[0, -1.j],
                    [1.j, 0]])
    return Qobj(mat, dims=[[2], [2]])


def z_gate():
    mat = np.array([[1, 0],
                    [0, -1]])
    return Qobj(mat, dims=[[2], [2]])


def s_gate():
    mat = np.array([[1.,   0],
                    [0., 1.j]])
    return Qobj(mat, dims=[[2], [2]])


def t_gate():
    mat = np.array([[1.,   0],
                    [0., e ** (1.j * (pi / 4))]])
    return Qobj(mat, dims=[[2], [2]])


def validator(func):
    def wrapper(self, *args, **kwargs):
        for q in args:
            if type(q) is int:
                assert q < self.size, 'qubit index out of range'
                assert q not in self.measured_qubits, 'qubit has been measured'
        if func.__name__ != 'measure':
            self._cache = None
        return func(self, *args, **kwargs)

    return wrapper


class Circuit:
    """Class for a quantum circuit.

    Attributes:
        size (int): the number of qubits in the circuit.
        gates (List[GATE_INFO_TYPE]): a list of commands bound to register.
        measured_qubits (List[int]): a list of indices of measured qubits.
    """

    def __init__(self, size: int) -> None:
        """Constructor for quantum circuit.

        Args:
            size (int): the number of qubits used in circuit.
        """

        self.size: int = size
        self.gates: List[GATE_INFO_TYPE] = []
        self.measured_qubits: List[int] = []
        self._cache: Optional[np.ndarray] = None

    def get_unitary_matrix(self) -> np.ndarray:
        """Method to get unitary matrix of circuit without measurement.

        Returns:
            np.ndarray: the matrix for the circuit operations.
        """

        if self._cache is None:
            if len(self.gates) == 0:
                self._cache = np.identity(2 ** self.size)
                return self._cache

            qc = QubitCircuit(self.size)
            qc.user_gates = {"X": x_gate,
                             "Y": y_gate,
                             "Z": z_gate,
                             "S": s_gate,
                             "T": t_gate}
            for gate in self.gates:
                name, indices, arg = gate
                if name == 'h':
                    qc.add_gate('SNOT', indices[0])
                elif name == 'x':
                    qc.add_gate('X', indices[0])
                elif name == 'y':
                    qc.add_gate('Y', indices[0])
                elif name == 'z':
                    qc.add_gate('Z', indices[0])
                elif name == 'cx':
                    qc.add_gate('CNOT', controls=indices[0], targets=indices[1])
                elif name == 'ccx':
                    qc.add_gate('TOFFOLI', controls=indices[:2], targets=indices[2])
                elif name == 'swap':
                    qc.add_gate('SWAP', indices)
                elif name == 't':
                    qc.add_gate('T', indices[0])
                elif name == 's':
                    qc.add_gate('S', indices[0])
                elif name == 'phase':
                    qc.add_gate('PHASEGATE', indices[0], arg_value=arg)
                else:
                    raise NotImplementedError
            self._cache = gate_sequence_product(qc.propagators()).full()

        return self._cache

    def serialize(self) -> Dict:
        gates = [{"name": g_name, "indices": indices, "arg": arg}
                 for g_name, indices, arg in self.gates]
        return {"size": self.size, "gates": gates,
                "measured_qubits": self.measured_qubits}

    def deserialize(self, json_data: Dict):
        self.size = json_data["size"]
        for gate in json_data["gates"]:
            name: str = gate["name"]
            indices: List[int] = gate["indices"]
            arg: float = gate["arg"]
            self.gates.append([name, indices, arg])
        self.measured_qubits = json_data["measured_qubits"]
        self._cache = None

    @validator
    def h(self, qubit: int):
        """Method to apply single-qubit Hadamard gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.gates.append(['h', [qubit], None])

    @validator
    def x(self, qubit: int):
        """Method to apply single-qubit Pauli-X gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.gates.append(['x', [qubit], None])

    @validator
    def y(self, qubit: int):
        """Method to apply single-qubit Pauli-Y gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.gates.append(['y', [qubit], None])

    @validator
    def z(self, qubit: int):
        """Method to apply single-qubit Pauli-Z gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.gates.append(['z', [qubit], None])

    @validator
    def cx(self, control: int, target: int):
        """Method to apply Control-X gate on three qubits.

        Args:
            control (int): the index of control1 in the circuit.
            target (int): the index of target in the circuit.
        """

        self.gates.append(['cx', [control, target], None])

    @validator
    def ccx(self, control1: int, control2: int, target: int):
        """Method to apply Toffoli gate on three qubits.

        Args:
            control1 (int): the index of control1 in the circuit.
            control2 (int): the index of control2 in the circuit.
            target (int): the index of target in the circuit.
        """

        self.gates.append(['ccx', [control1, control2, target], None])

    @validator
    def swap(self, qubit1: int, qubit2: int):
        """Method to apply SWAP gate on two qubits.

        Args:
            qubit1 (int): the index of qubit1 in the circuit.
            qubit2 (int): the index of qubit2 in the circuit.
        """

        self.gates.append(['swap', [qubit1, qubit2], None])

    @validator
    def t(self, qubit: int):
        """Method to apply single T gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.gates.append(['t', [qubit], None])

    @validator
    def s(self, qubit: int):
        """Method to apply single S gate on a qubit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.gates.append(['s', [qubit], None])

    @validator
    def phase(self, qubit: int, theta: float):
        """Method to apply a phase gate to a qubit.

        Args:
            qubit (int): index of the qubit in the circuit.
            theta (float): phase to apply
        """

        self.gates.append(['phase', [qubit], theta])

    @validator
    def measure(self, qubit: int):
        """Method to measure quantum bit into classical bit.

        Args:
            qubit (int): the index of qubit in the circuit.
        """

        self.measured_qubits.append(qubit)
