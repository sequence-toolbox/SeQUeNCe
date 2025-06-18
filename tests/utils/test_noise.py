import numpy as np
import pytest
from sequence.utils.noise import Noise
from sequence.components.circuit import Circuit

# Pauli matrices
_I = np.eye(2, dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)

# All 2-qubit Paulis
_TWO_QUBIT_PAULIS = [np.kron(a, b) for a in (_I, _X, _Y, _Z) for b in (_I, _X, _Y, _Z)]


def depolarise_manual(rho: np.ndarray, p: float) -> np.ndarray:
    """Manual two-qubit depolarising channel."""
    identity = np.kron(_I, _I)
    out = (1 - p) * rho.copy()
    weight = p / (len(_TWO_QUBIT_PAULIS) - 1)
    for P in _TWO_QUBIT_PAULIS:
        if not np.allclose(P, identity):
            out += weight * (P @ rho @ P.conj().T)
    return out


def test_two_qubit_depolarising_agrees():
    """Noise.apply_depolarizing_noise matches our manual implementation."""
    p = 0.3
    # |00><00|
    ket00 = np.kron([1, 0], [1, 0]).astype(complex)
    rho00 = np.outer(ket00, ket00.conj())

    rho_noise = Noise.apply_depolarizing_noise(rho=rho00, p=p, qubits=[0, 1], keys=[0, 1])
    rho_manual = depolarise_manual(rho00, p)

    assert np.allclose(rho_noise, rho_manual, atol=1e-12), "Channel outputs differ"
    assert np.isclose(np.trace(rho_noise), 1.0, atol=1e-12), "Trace not preserved"
    assert np.allclose(rho_noise, rho_noise.conj().T, atol=1e-12), "Result not Hermitian"


def test_measurement_noise_extremes():
    """For error_rate=0 no flip, for error_rate=1 always flip."""
    # no flip when rate=0
    circuit = Circuit(size=1)
    noisy = Noise.apply_measurement_noise(circuit, meas_error_rate=0.0, qubit_index=0)
    assert noisy.gates == [], "With error_rate=0, circuit should be unchanged"

    # always flip when rate=1
    circuit = Circuit(size=1)
    noisy = Noise.apply_measurement_noise(circuit, meas_error_rate=1.0, qubit_index=0)
    ops = [gate[0] for gate in noisy.gates]
    assert "x" in ops, "With error_rate=1, an X gate should have been applied"


def test_depolarizing_identity():
    """Depolarizing with p=0 returns the original two-qubit state."""
    rng = np.random.default_rng(42)
    # build a random pure two-qubit state
    vec = rng.random(4) + 1j * rng.random(4)
    vec /= np.linalg.norm(vec)
    rho = np.outer(vec, vec.conj())

    rho_out = Noise.apply_depolarizing_noise(rho=rho, p=0.0, qubits=[0, 1], keys=[0, 1])
    assert np.allclose(rho_out, rho, atol=1e-14), "p=0 should act as identity"
