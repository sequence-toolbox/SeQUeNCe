'''useful constants
'''

from typing import Final
from numpy import array


# speed of light in (m / pico second)
SPEED_OF_LIGHT: Final = 2e-4

SQRT_HALF: Final = 0.5 ** 0.5

# four Bell states
PHI_PLUS: Final  = array([SQRT_HALF, 0, 0,  SQRT_HALF])
PHI_MINUS: Final = array([SQRT_HALF, 0, 0, -SQRT_HALF])
PSI_PLUS: Final  = array([0, SQRT_HALF,  SQRT_HALF, 0])
PSI_MINUS: Final = array([0, SQRT_HALF, -SQRT_HALF, 0])

# machine epsilon, i.e., a small number
EPSILON: Final = 1e-7

# convert to picosecond
NANOSECOND: Final  = 1e3
MICROSECOND: Final = 1e6
MILLISECOND: Final = 1e9
SECOND: Final      = 1e12