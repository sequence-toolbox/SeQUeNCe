import numpy
import pytest

from sequence.kernel.timeline import Timeline
from sequence.components.photon import *
from sequence.components.bsm import *
from sequence.utils.encoding import *


numpy.random.seed(0)


class Parent():
        def __init__(self):
            self.results = []

        def pop(self, **kwargs):
            entity = kwargs.get("entity")
            if entity == "BSM":
                res=kwargs.get("res")
                self.results.append(res)
            else:
                raise Exception("invalid pop")


def test_construct_func():
    tl = Timeline()
    detectors2 = [{}] * 2
    detectors4 = [{}] * 4

    # unknown encoding scheme
    with pytest.raises(Exception):
        bsm = make_bsm("bsm", tl, encoding_type="unknown", detectors=detectors4)

    # implemented encoding schemes
    polar_bsm = make_bsm("bsm", tl, encoding_type="polarization", detectors=detectors4)
    time_bin_bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors2)
    ensemble_bsm = make_bsm("bsm", tl, encoding_type="ensemble", detectors=detectors2)
    atom_bsm = make_bsm("bsm", tl, encoding_type="single_atom", detectors=detectors2)

    assert type(polar_bsm) == PolarizationBSM
    assert type(time_bin_bsm) == TimeBinBSM
    assert type(ensemble_bsm) == EnsembleBSM
    assert type(atom_bsm) == SingleAtomBSM

def test_base_get():
    tl = Timeline()
    photon1 = Photon("", tl, location=1)
    photon2 = Photon("", tl, location=2)
    photon3 = Photon("", tl, location=3)
    photon1_2 = Photon("", tl, location=1)
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)

    bsm.get(photon1)
    assert len(bsm.photons) == 1

    # same location
    bsm.get(photon1_2)
    assert len(bsm.photons) == 1

    # different location
    bsm.get(photon2)
    assert len(bsm.photons) == 2

    # later time
    tl.time = 1
    bsm.get(photon3)
    assert len(bsm.photons) == 1

def test_polarization_get():
    tl = Timeline()
    detectors = [{}] * 4
    bsm = make_bsm("bsm", tl, encoding_type="polarization", detectors=detectors)
    parent = Parent()
    bsm.parents.append(parent)

    # get 2 photons in orthogonal states (map to Psi+)
    p1 = Photon("p1", tl, location=1, quantum_state=[complex(1), complex(0)])
    p2 = Photon("p2", tl, location=2, quantum_state=[complex(0), complex(1)])
    bsm.get(p1)
    bsm.get(p2)

    assert len(parent.results) == 1

    # get 2 photons in same state (map to Phi+ / can't measure)
    tl.time = 1e6
    p3 = Photon("p3", tl, location=1, quantum_state=[complex(1), complex(0)])
    p4 = Photon("p4", tl, location=2, quantum_state=[complex(1), complex(0)])
    bsm.get(p3)
    bsm.get(p4)

    assert len(parent.results) == 1

def test_polarization_pop():
    tl = Timeline()
    detectors = [{}] * 4
    bsm = make_bsm("bsm", tl, encoding_type="polarization", detectors=detectors)
    parent = Parent()
    bsm.parents.append(parent)
    detector_list = bsm.detectors

    # test Psi+
    bsm.pop(detector=detector_list[0], time=0)
    bsm.pop(detector=detector_list[1], time=0)

    assert len(parent.results) == 1
    assert parent.results[0] == 0

    # test Psi-
    bsm.pop(detector=detector_list[0], time=1)
    bsm.pop(detector=detector_list[3], time=1)

    assert len(parent.results) == 2
    assert parent.results[1] == 1

    # test not matching times
    bsm.pop(detector=detector_list[0], time=2)
    bsm.pop(detector=detector_list[3], time=3)

    assert len(parent.results) == 2

    # test invalid measurement
    bsm.pop(detector=detector_list[0], time=4)
    bsm.pop(detector=detector_list[2], time=4)
    
    assert len(parent.results) == 2

def test_time_bin_get():
    # TODO
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)
    parent = Parent()
    bsm.parents.append(parent)
    detector_list = bsm.detectors

    # get 2 photons in orthogonal states (map to Psi+)
    p1 = Photon("p1", tl, encoding_type=time_bin, location=1, quantum_state=[complex(1), complex(0)])
    p2 = Photon("p2", tl, encoding_type=time_bin, location=2, quantum_state=[complex(0), complex(1)])
    bsm.get(p1)
    bsm.get(p2)

    assert len(parent.results) == 1

    # get 2 photons in same state (map to Phi+ / can't measure)
    tl.time = 1e6
    p3 = Photon("p3", tl, encoding_type=time_bin, location=1, quantum_state=[complex(1), complex(0)])
    p4 = Photon("p4", tl, encoding_type=time_bin, location=2, quantum_state=[complex(1), complex(0)])
    bsm.get(p3)
    bsm.get(p4)

    assert len(parent.results) == 1

def test_time_bin_pop():
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)
    parent = Parent()
    bsm.parents.append(parent)
    detector_list = bsm.detectors

    # test Psi+
    bsm.pop(detector=detector_list[0], time=0)
    bsm.pop(detector=detector_list[0], time=0+time_bin["bin_separation"])

    assert len(parent.results) == 1
    assert parent.results[0] == 0

    # test Psi-
    bsm.pop(detector=detector_list[0], time=1e6)
    bsm.pop(detector=detector_list[1], time=1e6+time_bin["bin_separation"])

    assert len(parent.results) == 2
    assert parent.results[1] == 1

    # test invalid time separation
    bsm.pop(detector=detector_list[0], time=2e6)
    bsm.pop(detector=detector_list[0], time=2e6)

    assert len(parent.results) == 2

    bsm.pop(detector=detector_list[0], time=3e6)
    bsm.pop(detector=detector_list[0], time=4e6)

    assert len(parent.results) == 2

def test_ensemble_get():
    # TODO
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="ensemble", detectors=detectors)

def test_single_atom_get():
    # TODO
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="single_atom", detectors=detectors)


