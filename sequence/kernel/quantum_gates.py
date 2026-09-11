"""Canonical matrix definitions and metadata for qubit gates.

The circuit and quantum-manager backends use this module as their shared source
of gate semantics. Execution details, such as building a full-system unitary or
contracting a small gate into a state tensor, remain the responsibility of the
consumer.

There are two categories of gates: fixed and parameterized. 
15 fixed gates and 1 parameterized gate are defined in this module.
Identity is not counted as a gate, but is included in the PAULI_GATES dictionary.
"""

import numpy as np
from numpy.typing import NDArray

from ..constants import SQRT_HALF


GateMatrix = NDArray[np.complex128]

_I = np.array([[1, 0],
               [0, 1]],
               dtype=complex)

_H = SQRT_HALF * np.array([[1, 1],
                           [1, -1]],
                           dtype=complex)

_X = np.array([[0, 1],
               [1, 0]],
               dtype=complex)

_Y = np.array([[0, -1j],
               [1j, 0]],
               dtype=complex)

_Z = np.array([[1, 0],
               [0, -1]],
               dtype=complex)

_S = np.array([[1, 0],
               [0, 1j]],
               dtype=complex)

_SDG = np.array([[1, 0],
                 [0, -1j]],
                 dtype=complex)

_T = np.array([[1, 0],
               [0, np.exp(1j * np.pi / 4)]],
               dtype=complex)

_CX = np.array([[1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1],
                [0, 0, 1, 0]],
                dtype=complex)

_CZ = np.array([[1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, -1]],
                dtype=complex)

_SWAP = np.array([[1, 0, 0, 0],
                  [0, 0, 1, 0],
                  [0, 1, 0, 0],
                  [0, 0, 0, 1]],
                  dtype=complex)

_CCX = np.array([[1, 0, 0, 0, 0, 0, 0, 0],
                 [0, 1, 0, 0, 0, 0, 0, 0],
                 [0, 0, 1, 0, 0, 0, 0, 0],
                 [0, 0, 0, 1, 0, 0, 0, 0],
                 [0, 0, 0, 0, 1, 0, 0, 0],
                 [0, 0, 0, 0, 0, 1, 0, 0],
                 [0, 0, 0, 0, 0, 0, 0, 1],
                 [0, 0, 0, 0, 0, 0, 1, 0]],
                 dtype=complex)

_ROOT_IZ = SQRT_HALF * np.array([[1 + 1j, 0],
                                 [0, 1 - 1j]],
                                 dtype=complex)

_MINUS_ROOT_IZ = SQRT_HALF * np.array([[1 - 1j, 0],
                                       [0, 1 + 1j]],
                                       dtype=complex)

_ROOT_IY = SQRT_HALF * np.array([[1, 1],
                                 [-1, 1]],
                                 dtype=complex)

_MINUS_ROOT_IY = SQRT_HALF * np.array([[1, -1],
                                       [1, 1]],
                                       dtype=complex)

def phase_gate(theta: float) -> GateMatrix:
    """Return the single-qubit phase-gate matrix for ``theta`` radians.

    Args:
        theta (float): phase angle in radians.

    Return:
        GateMatrix: 2x2 matrix for the phase gate.
    """
    return np.array([[1, 0],
                     [0, np.exp(1j * theta)]],
                     dtype=complex)

_FIXED_GATES: dict[str, GateMatrix] = {
    "h": _H, "x": _X, "y": _Y, "z": _Z, "s": _S, "sdg": _SDG, "t": _T,
    "cx": _CX, "cz": _CZ, "swap": _SWAP, "ccx": _CCX,
    "root_iZ": _ROOT_IZ, "minus_root_iZ": _MINUS_ROOT_IZ,
    "root_iY": _ROOT_IY, "minus_root_iY": _MINUS_ROOT_IY
}

PAULI_GATES = {"I": _I, "X": _X, "Y": _Y, "Z": _Z}

# Number of qubits acted on by each gate.
GATE_ARITIES = {
    "h": 1, "x": 1, "y": 1, "z": 1, "s": 1, "sdg": 1, "t": 1, "phase": 1,
    "cx": 2, "cz": 2, "swap": 2, "ccx": 3,
    "root_iZ": 1, "minus_root_iZ": 1, "root_iY": 1, "minus_root_iY": 1
}

SUPPORTED_GATES = set(GATE_ARITIES)


def gate_matrix(name: str, arg: float | None = None) -> GateMatrix:
    """Return the canonical small matrix for a gate instruction.

    Args:
        name (str): circuit gate name.
        arg (float | None): gate parameter, required by parameterized gates.

    Returns:
        GateMatrix: matrix acting only on the gate's target qubits.

    Raises:
        ValueError: if the gate is unknown or a required argument is absent.
    """
    if name == "phase":
        if arg is None:
            raise ValueError("Gate 'phase' requires an angle.")
        return phase_gate(arg)
    try:
        return _FIXED_GATES[name]
    except KeyError:
        raise ValueError(f"Unsupported gate: {name}") from None
