"""Density matrix quantum state formalism."""

import numpy as np

from .base import OneDimensionInput, State, TwoDimensionInput


class DensityState(State):
    """Class for representing a quantum state in the density matrix formalism.

    Attributes:
        state (np.array): density matrix values. NxN matrix with N = d ** len(keys), where d is dimension of elementary
            Hilbert space. Default is d = 2 for qubits.
        keys (list[int]): list of keys (subsystems) associated with this state.
        truncation (int): maximally allowed number of excited states for elementary subsystems.
            Default is 1 for qubit. dim = truncation + 1
    """

    def __init__(self, state: OneDimensionInput | TwoDimensionInput, keys: list[int], truncation: int = 1):
        """Constructor for density state class.

        Args:
            state: density matrix elements given as a 2D array-like object. If the input is 1D, it is treated as a
                pure state vector and converted to a density matrix with the outer product.
            keys (list[int]): list of keys to this state in quantum manager.
            truncation (int): maximally allowed number of excited states for elementary subsystems.
                Default is 1 for qubit. dim = truncation + 1
        """

        super().__init__()
        self.truncation = truncation
        dim = self.truncation + 1  # dimension of element Hilbert space

        state = np.array(state, dtype=complex)
        if state.ndim == 1:
            state = np.outer(state, state.conj())
        elif state.ndim != 2:
            raise ValueError("Density matrix state must be a 1D state vector or a 2D matrix.")
        if state.shape[0] != state.shape[1]:
            raise ValueError("Density matrix must be square.")

        # check formatting
        assert abs(np.trace(np.array(state)) - 1) < 0.01, "density matrix trace must be 1"

        num_subsystems = np.log(len(state)) / np.log(dim)
        assert dim ** int(round(num_subsystems)) == len(state), (
            "Length of amplitudes should be d ** n, "
            "where d is subsystem Hilbert space dimension and n is the number of subsystems. "
            f"Actual amplitude length: {len(state)}, dim: {dim}, num subsystems: {num_subsystems}")
        num_subsystems = int(round(num_subsystems))
        assert num_subsystems == len(keys), (
            "Length of amplitudes should be d ** n, "
            "where d is subsystem Hilbert space dimension and n is the number of subsystems. "
            f"Amplitude length: {len(state)}, expected subsystems: {num_subsystems}, num keys: {len(keys)}")
        self.state = state
        self.keys = keys
