import numpy as np
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


def test_apply_depolarizing_noise():
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



def test_apply_measurement_noise():
    """Test measurement noise behavior at edge cases: 0 (no flip) and 1 (always flip)."""
    
    # Case 1: error_rate = 0 → no flip should occur
    circuit = Circuit(size=1)
    Noise.apply_measurement_noise(circuit, meas_error_rate=0.0, qubit_index=0)
    assert circuit.gates == [], "With error_rate=0, circuit should remain unchanged"

    # Case 2: error_rate = 1 → flip (X gate) should always occur
    circuit = Circuit(size=1)
    Noise.apply_measurement_noise(circuit, meas_error_rate=1.0, qubit_index=0)
    ops = [gate[0] for gate in circuit.gates]
    assert "x" in ops or "X" in ops, "With error_rate=1, an X gate should have been applied"
