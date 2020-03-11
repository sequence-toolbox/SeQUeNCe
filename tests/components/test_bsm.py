import numpy
import pytest

from sequence.kernel.timeline import Timeline
from sequence.components.photon import *
from sequence.components.bsm import *


numpy.random.seed(0)


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

def test_time_bin_get():
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)

def test_ensemble_get():
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="ensemble", detectors=detectors)

def test_single_atom_get():
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="single_atom", detectors=detectors)


