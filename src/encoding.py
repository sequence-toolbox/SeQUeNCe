import math


polarization =\
    {"name": "polarization",
     "bases": [[[complex(1), complex(0)], [complex(0), complex(1)]],
               [[complex(math.sqrt(2)), complex(math.sqrt(2))], [complex(-math.sqrt(2)), complex(math.sqrt(2))]]]
     }

time_bin =\
    {"name": "time_bin",
     "bases": [[[complex(1), complex(0)], [complex(0), complex(1)]],
               [[complex(math.sqrt(2)), complex(math.sqrt(2))], [complex(math.sqrt(2)), complex(-math.sqrt(2))]]],
     "bin_separation": 1000  # measured in ps
     }
