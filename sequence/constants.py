"""useful constants"""

from typing import Final

# speed of light in (m / pico second)
SPEED_OF_LIGHT: Final = 2e-4

# |0> and |1>
KET0: Final = (1, 0)
KET1: Final = (0, 1)

# four Bell states
SQRT_HALF: Final = 0.5 ** 0.5
PHI_PLUS:  Final = (SQRT_HALF, 0, 0,  SQRT_HALF)
PHI_MINUS: Final = (SQRT_HALF, 0, 0, -SQRT_HALF)
PSI_PLUS:  Final = (0, SQRT_HALF,  SQRT_HALF, 0)
PSI_MINUS: Final = (0, SQRT_HALF, -SQRT_HALF, 0)

# machine epsilon, i.e., a small number
EPSILON: Final = 1e-8

# convert to picosecond
NANOSECOND:  Final = 10**3
MICROSECOND: Final = 10**6
MILLISECOND: Final = 10**9
SECOND:      Final = 10**12
