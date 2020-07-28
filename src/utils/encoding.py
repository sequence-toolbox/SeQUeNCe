from math import sqrt


polarization =\
    {"name": "polarization",
     "bases": [[[complex(1), complex(0)], [complex(0), complex(1)]],
               [[complex(sqrt(1 / 2)), complex(sqrt(1 / 2))], [complex(-sqrt(1 / 2)), complex(sqrt(1 / 2))]]]
     }

time_bin = \
    {"name": "time_bin",
     "bases": [[[complex(1), complex(0)], [complex(0), complex(1)]],
               [[complex(sqrt(1 / 2)), complex(sqrt(1 / 2))], [complex(sqrt(1 / 2)), complex(-sqrt(1 / 2))]]],
     "bin_separation": 1400  # measured in ps
     }

# ensemble must be copied by photon so the memory field can be overwritten    
ensemble =\
    {"name": "ensemble",
     "bases": [[[complex(1), complex(0)], [complex(0), complex(1)]],
               None],
     "memory": None  # overwritten by photon
     }

single_atom =\
    {"name": "single_atom",
     "bases": [[[complex(1), complex(0)], [complex(0), complex(1)]],
               None],
     "memory": None  # overwritten by photon
     }
