from numpy import random
from sequence.components.photon import Photon
from sequence.components.switch import Switch
from sequence.kernel.timeline import Timeline
from sequence.utils.encoding import time_bin

random.seed(0)
FREQ = 1e6


def create_switch(basis_list, photons):
    class Receiver():
        def __init__(self, tl):
            self.timeline = tl
            self.log = []

        def get(self, photon=None):
            self.log.append((self.timeline.now(), photon))

    tl = Timeline()
    sw = Switch("sw", tl)
    r1 = Receiver(tl)
    r2 = Receiver(tl)
    sw.set_detector(r1)
    sw.set_interferometer(r2)
    sw.set_basis_list(basis_list, 0, FREQ)

    tl.init()
    for i, photon in enumerate(photons):
        tl.time = 1e12 / FREQ * i
        sw.get(photons[i])
    tl.time = 0
    tl.run()

    return r1.log, r2.log


def test_Switch_get():
    # z-basis measure |e> and |l>
    photons = [Photon('', encoding_type=time_bin, quantum_state=time_bin["bases"][0][i]) for i in range(2)]
    log1, log2 = create_switch([0] * 2, photons)
    expects = [0, 1e12 / FREQ + time_bin["bin_separation"]]
    for i, log in enumerate(log1):
        time, photon = log
        assert time == expects[i]
        assert photon is None
    assert len(log2) == 0

    # z-basis measure |e+l> and |e-l>
    photons = [Photon('', encoding_type=time_bin, quantum_state=time_bin["bases"][0][random.randint(2)]) for _ in
               range(2000)]
    log1, log2 = create_switch([0] * 2000, photons)
    assert len(log2) == 0
    counter1 = 0
    counter2 = 0
    for time, photon in log1:
        assert photon is None
        time = time % (1e12 / FREQ)
        if time == 0:
            counter1 += 1
        elif time == time_bin["bin_separation"]:
            counter2 += 1
        else:
            assert False
    assert abs(counter2 / counter1 - 1) < 0.1

    # x-basis get photons
    photons = [Photon('',
                      encoding_type=time_bin,
                      quantum_state=time_bin["bases"][random.randint(2)][random.randint(2)]) for _ in range(2000)]
    log1, log2 = create_switch([1] * 2000, photons)
    assert len(log1) == 0
    for time, photon in log1:
        time = time % (1e12 / FREQ)
        assert time == 0
        assert photon is not None
