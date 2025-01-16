# %matplotlib inline
from pathlib import Path
from copy import copy
from matplotlib import pyplot as plt

import numpy as np
from scipy import optimize

from sequence.components.polarizationFock.node_definitions import *
from sequence.components.polarizationFock_Tensor.light_source import SPDCSource

from sequence.kernel.timeline import Timeline
from sequence.kernel.quantum_manager import POLARIZATION_FOCK_FORMALISM, POLARIZATION_FOCK_TENSOR_FORMALISM

import json
import csv


timeline = Timeline(formalism = POLARIZATION_FOCK_TENSOR_FORMALISM, truncation = 3, error_tolerance = 1e-10)

photon1, photon2 = SPDCSource("src", timeline).emit(num_emissions = 1, debug = True)
