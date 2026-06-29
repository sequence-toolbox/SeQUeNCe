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


def depolarise_manual_single_qubit(rho: np.ndarray, p: float) -> np.ndarray:
    """Manual single-qubit depolarising channel."""
    out = (1 - p) * rho.copy()
    weight = p / 3
    for P in (_X, _Y, _Z):
        out += weight * (P @ rho @ P.conj().T)
    return out


def depolarise_manual_two_qubit(rho: np.ndarray, p: float) -> np.ndarray:
    """Manual two-qubit depolarising channel."""
    identity = np.kron(_I, _I)
    out = (1 - p) * rho.copy()
    weight = p / (len(_TWO_QUBIT_PAULIS) - 1)
    for P in _TWO_QUBIT_PAULIS:
        if not np.allclose(P, identity):
            out += weight * (P @ rho @ P.conj().T)
    return out


def depolarise_manual_two_qubit_embedded(rho: np.ndarray, p: float, target_positions: list[int], n: int) -> np.ndarray:
    """Manual two-qubit depolarising channel embedded in an n-qubit state."""
    out = (1 - p) * rho.copy()
    weight = p / (len(_TWO_QUBIT_PAULIS) - 1)

    for target_paulis in [(a, b) for a in (_I, _X, _Y, _Z) for b in (_I, _X, _Y, _Z)][1:]:
        factors = []
        target_factor = 0
        for position in range(n):
            if position in target_positions:
                factors.append(target_paulis[target_factor])
                target_factor += 1
            else:
                factors.append(_I)

        full_op = factors[0]
        for factor in factors[1:]:
            full_op = np.kron(full_op, factor)
        out += weight * (full_op @ rho @ full_op.conj().T)

    return out


def test_apply_depolarizing_noise_two_qubit():
    """Noise.apply_depolarizing_noise matches our manual implementation."""
    p = 0.3
    # |00><00|
    ket00 = np.kron([1, 0], [1, 0]).astype(complex)
    rho00 = np.outer(ket00, ket00.conj())

    rho_noise = Noise.apply_depolarizing_noise(rho=rho00, p=p, qubits=[0, 1], keys=[0, 1])
    rho_manual = depolarise_manual_two_qubit(rho00, p)

    assert np.allclose(rho_noise, rho_manual, atol=1e-12), "Channel outputs differ"
    assert np.isclose(np.trace(rho_noise), 1.0, atol=1e-12), "Trace not preserved"
    assert np.allclose(rho_noise, rho_noise.conj().T, atol=1e-12), "Result not Hermitian"


def test_apply_depolarizing_noise_two_qubit_noncontiguous_keys():
    """Two-qubit depolarising channel works when qubit labels are non-contiguous."""
    p = 0.3
    keys = [0, 2, 3]
    qubits = [0, 3]

    # |000><000| with tensor-product order defined by keys.
    ket000 = np.kron(np.kron([1, 0], [1, 0]), [1, 0]).astype(complex)
    rho000 = np.outer(ket000, ket000.conj())

    rho_noise = Noise.apply_depolarizing_noise(rho=rho000, p=p, qubits=qubits, keys=keys)
    rho_manual = depolarise_manual_two_qubit_embedded(rho000, p, target_positions=[keys.index(q) for q in qubits], n=len(keys))

    assert np.allclose(rho_noise, rho_manual, atol=1e-12), "Channel outputs differ"
    assert np.isclose(np.trace(rho_noise), 1.0, atol=1e-12), "Trace not preserved"
    assert np.allclose(rho_noise, rho_noise.conj().T, atol=1e-12), "Result not Hermitian"


def test_apply_depolarizing_noise_single_qubit():
    """Single-qubit depolarising channel matches the standard k=1 channel."""
    p = 0.3
    # |0><0|
    ket0 = np.array([1, 0], dtype=complex)
    rho0 = np.outer(ket0, ket0.conj())

    rho_noise = Noise.apply_depolarizing_noise(rho=rho0, p=p, qubits=[0], keys=[0])
    rho_manual = depolarise_manual_single_qubit(rho0, p)

    assert np.allclose(rho_noise, rho_manual, atol=1e-12), "Single-qubit channel outputs differ"
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
