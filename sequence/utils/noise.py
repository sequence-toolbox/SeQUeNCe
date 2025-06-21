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
    def apply_measurement_noise(circuit: "Circuit", meas_error_rate: float, qubit_index: int = 0): 
        """
        Applies classical measurement noise by flipping the qubit with probability η.

        With probability `meas_error_rate`, an X gate is applied to the specified qubit
        to simulate a bit-flip error in the measurement result.

        Parameters
        ----------
        circuit : Circuit
            The quantum circuit to modify. This function mutates the circuit in place
            by appending an X gate if a flip occurs.

        meas_error_rate : float
            Probability η (between 0 and 1) that the measurement result is incorrect.

        qubit_index : int, optional
            Index of the qubit to apply noise to (default is 0).

        Returns
        -------
        None
            This function does not return anything. It modifies the input circuit directly.

        Notes
        -----
        - Used to simulate classical readout errors after measurement.
        - The circuit is directly updated — no new object is returned.
        """
        if np.random.random() < meas_error_rate:
            circuit.x(qubit_index)


    @staticmethod
    def apply_depolarizing_noise(rho: np.ndarray, p: float, qubits: List[int], keys: List[int]) -> np.ndarray:
        """
        Apply depolarizing noise to selected qubits in an n-qubit density matrix.

        This function simulates the depolarizing channel:
            (rho) → (1 - p) * (rho) + (p / (4^k - 1)) * Σ_i P_i * (rho) * P_i†
        where:
            - k = len(qubits), the number of qubits affected (must be 1 or 2),
            - {P_i} is the set of all non-identity Pauli operators on those k qubits,
            - Each P_i is extended (lifted) to act on the full n-qubit system.

        The result is a noisy version of the original state, mixing in random Pauli errors
        on the selected qubits. This function returns a new density matrix that reflects
        this transformation.

        Parameters
        ----------
        rho : np.ndarray
            A (2^n x 2^n) density matrix representing an n-qubit state.
            The qubit ordering is determined by the `keys` list.

        p : float
            Depolarizing probability (0 ≤ p ≤ 1).
            - p = 0: state remains unchanged,
            - p = 1: selected qubits become maximally mixed.

        qubits : List[int]
            One or two qubit indices to apply noise to.
            These must appear in the `keys` list.

        keys : List[int]
            A permutation of [0, 1, ..., n-1] defining the tensor product order of qubits in `rho`.

            Each key corresponds to a qubit managed by QuantumManagerDensity. For example,
            keys = [3, 7, 1] means qubit 3 is treated as the first subsystem (most significant),
            7 as second, and 1 as third.

            This lets `rho` represent entangled states with flexible qubit ordering.
            The function uses this list to locate where each target qubit appears in the
            tensor product and apply noise accordingly.

        Returns
        -------
        np.ndarray
            The updated (2^n x 2^n) density matrix with depolarizing noise on the given qubits.

        Raises
        ------
        ValueError
            If p is not in [0, 1], if rho has the wrong shape,
            if qubits has length not in {1, 2}, or if any target qubit is missing from keys.

        Notes
        -----
        - After applying noise, update the simulation manually using:
          `quantum_manager.set(keys, new_rho)`. This function does not modify global state.
        - The function returns a new density matrix (does not mutate rho in-place) because
          noise channels are CPTP maps that return fresh quantum states.
        - The code finds each qubit's position in the tensor product using `keys`,
          and applies Pauli operators using Kronecker products to avoid reshuffling the full matrix.
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
