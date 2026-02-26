"""Shared constants used across SeQUeNCe.

This module centralizes immutable values that are reused by simulation and
network components, including:

- Physical constants (for example, speed of light in meters per picosecond).
- Canonical quantum state vectors (basis states and Bell states).
- Numerical tolerances (`EPSILON`) for floating-point comparisons.
- Time unit conversion factors in picoseconds (`NANOSECOND` to `SECOND`).
- Built-in formalism and protocol identifier strings.
"""

from typing import Final

#: Speed of light in meters per picosecond.
SPEED_OF_LIGHT: Final = 2e-4

#: Qubit computational basis state |0>.
KET0: Final = (1, 0)
#: Qubit computational basis state |1>.
KET1: Final = (0, 1)

#: Normalization factor 1/sqrt(2) used by Bell states.
SQRT_HALF: Final = 0.5 ** 0.5
#: Bell state |Phi+>.
PHI_PLUS:  Final = (SQRT_HALF, 0, 0,  SQRT_HALF)
#: Bell state |Phi->.
PHI_MINUS: Final = (SQRT_HALF, 0, 0, -SQRT_HALF)
#: Bell state |Psi+>.
PSI_PLUS:  Final = (0, SQRT_HALF,  SQRT_HALF, 0)
#: Bell state |Psi->.
PSI_MINUS: Final = (0, SQRT_HALF, -SQRT_HALF, 0)

#: Small tolerance value for floating-point comparisons.
EPSILON: Final = 1e-8

#: Number of picoseconds in one nanosecond.
NANOSECOND:  Final = 10**3
#: Number of picoseconds in one microsecond.
MICROSECOND: Final = 10**6
#: Number of picoseconds in one millisecond.
MILLISECOND: Final = 10**9
#: Number of picoseconds in one second.
SECOND:      Final = 10**12

#: Built-in ket-vector formalism identifier.
KET_STATE_FORMALISM: Final = "ket_vector"
#: Built-in density-matrix formalism identifier.
DENSITY_MATRIX_FORMALISM: Final = "density_matrix"
#: Built-in Fock density-matrix formalism identifier.
FOCK_DENSITY_MATRIX_FORMALISM: Final = "fock_density"
#: Built-in Bell-diagonal-state formalism identifier.
BELL_DIAGONAL_STATE_FORMALISM: Final = "bell_diagonal"

#: Built-in Barrett-Kok generation protocol identifier.
BARRET_KOK: Final = 'barret_kok'
#: Built-in single-heralded generation protocol identifier.
SINGLE_HERALDED: Final = 'single_heralded'
