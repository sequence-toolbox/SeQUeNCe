"""useful constants"""

from typing import Final
from numpy import array


# speed of light in (m / pico second)
SPEED_OF_LIGHT: Final = 2e-4

SQRT_HALF: Final = 0.5 ** 0.5

# four Bell states
PHI_PLUS: Final = array([SQRT_HALF, 0, 0,  SQRT_HALF])
PHI_MINUS: Final = array([SQRT_HALF, 0, 0, -SQRT_HALF])
PSI_PLUS: Final = array([0, SQRT_HALF,  SQRT_HALF, 0])
PSI_MINUS: Final = array([0, SQRT_HALF, -SQRT_HALF, 0])

# machine epsilon, i.e., a small number
EPSILON: Final = 1e-7

# convert to picosecond
NANOSECOND: Final = 1e3
MICROSECOND: Final = 1e6
MILLISECOND: Final = 1e9
SECOND: Final = 1e12

# for timeline formatting
NANOSECONDS_PER_MILLISECOND: Final = 1e6
PICOSECONDS_PER_NANOSECOND = NANOSECONDS_PER_MICROSECOND = MILLISECONDS_PER_SECOND = 1e3
SECONDS_PER_MINUTE = MINUTES_PER_HOUR = 60
CARRIAGE_RETURN = '\r'
SLEEP_SECONDS = 3
