"""Ket vector quantum state formalism."""

import math

import numpy as np

from .base import State
from ...constants import EPSILON


class KetState(State):
    """Class for representing a quantum state in the ket vector formalism.

    Attributes:
        state (np.array): state vector. Should be of length d ** len(keys), where d is dimension of elementary
            Hilbert space. Default is 2 for qubits.
        keys (list[int]): list of keys (subsystems) associated with this state.
        truncation (int): maximally allowed number of excited states for elementary subsystems.
                Default is 1 for qubit. dim = truncation + 1
    """

    def __init__(self, amplitudes: list[complex], keys: list[int], truncation: int = 1):
        """Constructor for ket state class.

        Args:
            amplitudes
            truncation (int): maximally allowed number of excited states for elementary subsystems.
                Default is 1 for qubit. dim = truncation + 1
        """
        super().__init__()
        self.truncation = truncation
        dim = self.truncation + 1  # dimension of element Hilbert space

        # check formatting
        assert all([abs(a) <= 1 + EPSILON for a in amplitudes]), "Illegal value with abs > 1 in ket vector"
        assert math.isclose(sum([abs(a) ** 2 for a in amplitudes]), 1), "Squared amplitudes do not sum to 1"

        num_subsystems = np.log(len(amplitudes)) / np.log(dim)
        assert dim ** int(round(num_subsystems)) == len(amplitudes),\
            "Length of amplitudes should be d ** n, " \
            "where d is subsystem Hilbert space dimension and n is the number of subsystems. " \
            "Actual amplitude length: {}, dim: {}, num subsystems: {}".format(len(amplitudes), dim, num_subsystems)
        num_subsystems = int(round(num_subsystems))
        assert num_subsystems == len(keys),\
            "Length of amplitudes should be d ** n, " \
            "where d is subsystem Hilbert space dimension and n is the number of subsystems. " \
            "Amplitude length: {}, expected subsystems: {}, num keys: {}".format(len(amplitudes), num_subsystems, len(keys))

        self.state = np.array(amplitudes, dtype=complex)
        self.keys = keys
