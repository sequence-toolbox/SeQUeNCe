import pytest
from numpy import random
from sequence.components.beam_splitter import BeamSplitter
from sequence.components.photon import Photon
from sequence.kernel.timeline import Timeline
from sequence.utils.encoding import polarization

random.seed(1)


def test_BeamSplitter_init():
    tl = Timeline()
    bs = BeamSplitter("bs", tl)
    tl.init()


class Receiver():
    def __init__(self, tl):
        self.timeline = tl
        self.log = []

    def get(self):
        self.log.append((self.timeline.now()))


def test_BeamSplitter_set_receiver():
    tl = Timeline()
    bs = BeamSplitter("bs", tl)
    receiver = Receiver(tl)
    bs.set_receiver(0, receiver)
    receiver = Receiver(tl)
    bs.set_receiver(1, receiver)
    receiver = Receiver(tl)
    with pytest.raises(Exception):
        bs.set_receiver(5, receiver)


def test_BeamSplitter_get():
    tl = Timeline()
    bs = BeamSplitter("bs", tl)
    receiver0 = Receiver(tl)
    bs.set_receiver(0, receiver0)
    receiver1 = Receiver(tl)
    bs.set_receiver(1, receiver1)

    frequency = 8e7
    start_time = 0
    basis_len = 1000
    basis_list = []

    # z-basis states, measurement
    for i in range(basis_len):
        basis_list.append(0)

    bs.set_basis_list(basis_list, start_time, frequency)

    bits = []
    for i in range(basis_len):
        time = 1e12 / frequency * i
        tl.time = time
        bit = random.randint(2)
        bits.append(bit)
        photon = Photon(str(i), quantum_state=polarization["bases"][0][bit])
        bs.get(photon)

    for i in range(basis_len):
        time = 1e12 / frequency * i
        r_i = bits[i]
        assert time in bs.receivers[r_i].log

    # x-basis states, measurement
    receiver0.log = []
    receiver1.log = []
    basis_list = []
    for i in range(basis_len):
        basis_list.append(1)

    bs.set_basis_list(basis_list, start_time, frequency)

    bits2 = []
    for i in range(basis_len):
        time = 1e12 / frequency * i
        tl.time = time
        bit = random.randint(2)
        bits2.append(bit)
        photon = Photon(str(i), quantum_state=polarization["bases"][1][bit])
        bs.get(photon)

    for i in range(basis_len):
        time = 1e12 / frequency * i
        r_i = bits2[i]
        assert time in bs.receivers[r_i].log

    # z-basis states, x-basis measurement
    receiver0.log = []
    receiver1.log = []
    basis_list = []
    for i in range(basis_len):
        basis_list.append(1)

    bs.set_basis_list(basis_list, start_time, frequency)

    bits = []
    for i in range(basis_len):
        time = 1e12 / frequency * i
        tl.time = time
        bit = random.randint(2)
        bits.append(bit)
        photon = Photon(str(i), quantum_state=polarization["bases"][0][bit])
        bs.get(photon)

    print(len(receiver1.log), len(receiver0.log))
    true_counter, false_counter = 0, 0
    for i in range(basis_len):
        time = 1e12 / frequency * i
        r_i = bits[i]
        if time in bs.receivers[r_i].log:
            true_counter += 1
        else:
            false_counter += 1
    assert true_counter / basis_len - 0.5 < 0.1
