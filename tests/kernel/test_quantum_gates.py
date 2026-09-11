"""Tests for canonical qubit-gate definitions."""

import numpy as np

from sequence.components.circuit import Circuit
from sequence.kernel.quantum_gates import GATE_ARITIES, gate_matrix


_FIXED_GATES = [
    ("h", lambda circuit: circuit.h(0)),
    ("x", lambda circuit: circuit.x(0)),
    ("y", lambda circuit: circuit.y(0)),
    ("z", lambda circuit: circuit.z(0)),
    ("s", lambda circuit: circuit.s(0)),
    ("sdg", lambda circuit: circuit.sdg(0)),
    ("t", lambda circuit: circuit.t(0)),
    ("cx", lambda circuit: circuit.cx(0, 1)),
    ("cz", lambda circuit: circuit.cz(0, 1)),
    ("swap", lambda circuit: circuit.swap(0, 1)),
    ("ccx", lambda circuit: circuit.ccx(0, 1, 2)),
    ("root_iZ", lambda circuit: circuit.root_iZ(0)),
    ("minus_root_iZ", lambda circuit: circuit.minus_root_iZ(0)),
    ("root_iY", lambda circuit: circuit.root_iY(0)),
    ("minus_root_iY", lambda circuit: circuit.minus_root_iY(0)),
]


def test_fixed_gate_matrices_match_circuit_unitaries():
    for name, build in _FIXED_GATES:
        circuit = Circuit(GATE_ARITIES[name])
        build(circuit)
        assert np.allclose(gate_matrix(name), circuit.get_unitary_matrix()), name


def test_phase_gate_matrix_matches_circuit_unitary():
    theta = 0.37
    circuit = Circuit(1)
    circuit.phase(0, theta)
    assert np.allclose(gate_matrix("phase", theta), circuit.get_unitary_matrix())


def test_fixed_gate_matrices_are_unitary():
    for name, _ in _FIXED_GATES:
        matrix = gate_matrix(name)
        assert matrix.shape == (2 ** GATE_ARITIES[name], 2 ** GATE_ARITIES[name]), name
        assert np.allclose(matrix.conj().T @ matrix, np.eye(matrix.shape[0])), name


def test_phase_gate_matrix_is_unitary():
    matrix = gate_matrix("phase", 0.37)
    assert matrix.shape == (2, 2)
    assert np.allclose(matrix.conj().T @ matrix, np.eye(2))
