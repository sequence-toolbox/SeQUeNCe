"""
Helper functions for Bell State Measurement Modules
"""
from .polarization_bsm import PolarizationBSM
from .time_bin_bsm import TimeBinBSM
from .single_atom_bsm import SingleAtomBSM
from .absorptive_bsm import AbsorptiveBSM

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline


def make_bsm(name, timeline: "Timeline", encoding_type='time_bin', phase_error=0, detectors=[]):
    """Function to construct BSM of specified type.

    Arguments:
        name (str): name to be used for BSM instance.
        timeline (Timeline): timeline to be used for BSM instance.
        encoding_type (str): type of BSM to generate (default "time_bin").
        phase_error (float): error to apply to incoming qubits (default 0).
        detectors (list[dict[str, any]): list of detector objects given as dicts (default []).
    """

    encoding_types = {'polarization': PolarizationBSM,
                      'time_bin': TimeBinBSM,
                      'single_atom': SingleAtomBSM,
                      'absorptive': AbsorptiveBSM}

    if encoding_type not in encoding_types:
        raise ValueError('encoding_type must be one of {}'.format(encoding_types))

    bsm_class = encoding_types[encoding_type]
    return bsm_class(name, timeline, phase_error, detectors)