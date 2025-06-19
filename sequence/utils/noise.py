import numpy as np
from sequence.components.circuit import Circuit
from typing import List

class Noise:
    """
    Provides static methods to simulate common quantum noise processes on circuits and density matrices.

    Supported noise models include:
    - Single-qubit depolarizing noise
    - Two-qubit depolarizing noise (standalone or full density matrix injection)
    - Measurement bit-flip errors
    - Noisy two-qubit gate application in circuits

    These methods support both circuit-level (via SeQUeNCe `Circuit` objects) and 
    density-matrix-level simulations, enabling realistic modeling of quantum errors 
    for testing protocols like quantum error correction or entanglement generation.

    All methods are stateless and can be used independently within simulation pipelines.
    """

    @staticmethod
    def apply_measurement_noise(circuit: "Circuit", meas_error_rate: float, qubit_index: int = 0) -> "Circuit":
        """
        Applies measurement error by flipping the qubit with probability η.

        Args:
            circuit (Circuit): The quantum circuit object.
            meas_error_rate (float): Measurement error probability (η).
            qubit_index (int): Qubit index to flip.

        Returns:
            Circuit: Modified circuit after applying noise.
        """
        if np.random.random() < meas_error_rate:
            circuit.x(qubit_index)
        return circuit


    @staticmethod
    def apply_depolarizing_noise(rho: np.ndarray, p: float, qubits: List[int], keys: List[int]) -> np.ndarray:
        """
        Apply single- or two-qubit depolarizing noise to a full n-qubit density matrix.

        This function implements the channel:
            rho -> (1 - p) * rho + (p / (4^k - 1)) * sum_i P_i * rho * P_i^dagger
        where k = len(qubits) (1 or 2), and {P_i} are all non-identity
        Pauli operators on those k qubits lifted to the full 2^n space.

        Parameters
        ----------
        rho : numpy.ndarray of shape (2**n, 2**n)
            The full density matrix for n qubits.
        p : float
            Depolarizing probability, between 0 and 1.
        qubits : list of int
            Qubit indices to which noise is applied (length 1 or 2).
        keys : list of int
            Permutation of [0, 1, ..., n-1] defining the order of qubits in the rows and columns of rho.

        Returns
        -------
        numpy.ndarray
            The density matrix after applying depolarizing noise.

        Raises
        ------
        ValueError
            If p is not in [0, 1], if rho has incorrect shape, or
            if qubits/keys are invalid.
        """
        # check probability
        if not (0.0 <= p <= 1.0):
            raise ValueError("Depolarizing probability must be between 0 and 1.")

        # determine number of qubits and validate rho shape
        n = len(keys)
        dim = 2 ** n
        if rho.shape != (dim, dim):
            raise ValueError(f"rho must have shape ({dim}, {dim}).")

        # validate qubit list
        k = len(qubits)
        if k not in (1, 2):
            raise ValueError("qubits must have length 1 or 2.")
        for q in qubits:
            if q not in keys:
                raise ValueError("each target qubit must appear in keys.")

        # define single-qubit Pauli matrices
        I = np.eye(2, dtype=complex)
        X = np.array([[0, 1], [1, 0]], dtype=complex)
        Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        Z = np.array([[1, 0], [0, -1]], dtype=complex)
        paulis = [I, X, Y, Z]

        # locate positions of target qubits in the tensor-product order
        positions = [keys.index(q) for q in qubits]

        # build list of non-identity Pauli operators lifted to full space
        pauli_ops: List[np.ndarray] = []
        idx_tuples = [(i, j) for i in range(4) for j in range(4)]
        for idx_tuple in idx_tuples:
            if all(i == 0 for i in idx_tuple):
                continue  # skip identity
            full_op = None
            for subsystem in range(n):
                if subsystem in positions:
                    idx = positions.index(subsystem)
                    P = paulis[idx_tuple[idx]]
                else:
                    P = I
                full_op = P if full_op is None else np.kron(full_op, P)
            pauli_ops.append(full_op)

        m = len(pauli_ops)  # should be 4^k - 1

        # apply depolarizing channel
        rho_noisy = (1.0 - p) * rho.copy()
        weight = p / m
        for P in pauli_ops:
            rho_noisy += weight * (P @ rho @ P.conj().T)

        return rho_noisy
