"""Definition of the quantum state classes.

This package defines classes used to track quantum states in SeQUeNCe.
The formalism-specific state classes are used by quantum managers, while
FreeQuantumState is used by individual photons that do not use a quantum manager.
"""

from .base import State
from .bell_diagonal import BellDiagonalState
from .density_matrix import DensityState
from .free import FreeQuantumState
from .ket_vector import KetState
from .tableau import TableauState

__all__ = [
    "State",
    "BellDiagonalState",
    "DensityState",
    "FreeQuantumState",
    "KetState",
    "TableauState",
]


def __dir__():
    return sorted(__all__)
