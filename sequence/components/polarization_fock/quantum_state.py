from abc import ABC
from typing import Tuple, Dict, List

from numpy import pi, cos, sin, arange, log, log2
from numpy.random import Generator
import numpy as np

from sequence.kernel.quantum_utils import *
import scipy.sparse as sp
from sequence.kernel.quantum_state import State

class SparseDensityState(State):
    """Class to represent an individual quantum state as a density matrix.

    Attributes:
        state (np.array): density matrix values. NxN matrix with N = d ** len(keys), where d is dimension of elementary
            Hilbert space. Default is d = 2 for qubits.
        keys (List[int]): list of keys (subsystems) associated with this state.
        truncation (int): maximally allowed number of excited states for elementary subsystems.
            Default is 1 for qubit. dim = truncation + 1
    """

    def __init__(self, state, keys: List[int], truncation: int = 1):
        """Constructor for density state class.

        Args:
            state (List[List[complex]]): density matrix elements given as a list.
                If the list is one-dimensional, will be converted to matrix with outer product operation.
            keys (List[int]): list of keys to this state in quantum manager.
            truncation (int): maximally allowed number of excited states for elementary subsystems.
                Default is 1 for qubit. dim = truncation + 1
        """

        super().__init__()
        self.truncation = truncation
        dim = (self.truncation + 1)**2  # dimension of PolarizationFock Hilbert space

        # Check type
        assert type(state) == sp.csr_matrix

        # check formatting

        # print("state:", state.A)

        assert abs(state.trace() - 1) < 0.01, f"density matrix trace must be 1. Got trace {state.trace()}"
        assert state.shape[0] == state.shape[1]

        num_subsystems = log(state.shape[0]) / log(dim)
        assert dim ** int(round(num_subsystems)) == state.shape[0], \
            "Length of amplitudes should be d ** n, " \
            "where d is subsystem Hilbert space dimension and n is the number of subsystems. " \
            "Actual amplitude length: {}, dim: {}, num subsystems: {}".format(
                state.shape[0], dim, num_subsystems
            )
        num_subsystems = int(round(num_subsystems))
        assert num_subsystems == len(keys), \
            "Length of amplitudes should be d ** n, " \
            "where d is subsystem Hilbert space dimension and n is the number of subsystems. " \
            "Amplitude length: {}, expected subsystems: {}, num keys: {}".format(
                state.shape[0], num_subsystems, len(keys)
            )

        self.state = state
        self.keys = keys
