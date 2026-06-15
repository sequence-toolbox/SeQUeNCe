"""Definition of the quantum state classes.

This package defines classes used to track quantum states in SeQUeNCe.
The formalism-specific state classes are used by quantum managers, while
FreeQuantumState is used by individual photons that do not use a quantum manager.
"""

from .base import OneDimensionInput, State, TwoDimensionInput
from .bell_diagonal import BellDiagonalState
from .density_matrix import DensityState
from .free import FreeQuantumState
from .ket_vector import KetState
from .stabilizer import StabilizerState

__all__ = [
    "State",
    "OneDimensionInput",
    "TwoDimensionInput",
    "BellDiagonalState",
    "DensityState",
    "FreeQuantumState",
    "KetState",
    "StabilizerState",
]


def __dir__():
    return sorted(__all__)
