"""Definitions of encoding schemes.

Encoding schemes are applied to photons and memories to track how quantum information is stored.
This includes the name of the encoding scheme, bases available, and any other necessary parameters.

Attributes:
    polarization (Dict[str, any]): defines the polarization encoding scheme, including the Z- and X-basis.
    time_bin (Dict[str, any]): defines the time bin encoding scheme, including the Z- and X-basis. Also defines the bin separation time.
    single_atom (Dict[str, any]): defines the single atom memory scheme, including the Z-basis.
"""

from math import sqrt


polarization =\
    {"name": "polarization",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))),
               ((complex(sqrt(1 / 2)), complex(sqrt(1 / 2))), (complex(-sqrt(1 / 2)), complex(sqrt(1 / 2))))]
     }

time_bin = \
    {"name": "time_bin",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))),
               ((complex(sqrt(1 / 2)), complex(sqrt(1 / 2))), (complex(sqrt(1 / 2)), complex(-sqrt(1 / 2))))],
     "bin_separation": 1400  # measured in ps
     }

# single_atom must be copied by photon so the memory field can be overwritten 
single_atom = \
    {"name": "single_atom",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))), None],
     "memory": None  # overwritten by photon
     }
