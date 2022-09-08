import numpy as np

from sequence.components.interferometer import Interferometer
from sequence.components.photon import Photon
from sequence.kernel.timeline import Timeline
from sequence.utils.encoding import time_bin


NUM_TRIALS = int(10e3)
SEED = 0


def create_intf(quantum_state):
    class Owner:
        def __init__(self):
            self.generator = np.random.default_rng(SEED)

        def get_generator(self):
            return self.generator

    class Receiver:
        def __init__(self, name, timeline):
            self.name = name
            self.timeline = timeline
            self.log = []

        def get(self):
            self.log.append(self.timeline.now())

    tl = Timeline()
    intfm = Interferometer("interferometer", tl, time_bin["bin_separation"])
    d0 = Receiver("d0", tl)
    d1 = Receiver("d1", tl)
    own = Owner()
    intfm.add_receiver(d0)
    intfm.add_receiver(d1)
    intfm.owner = own
    tl.init()

    for i in range(NUM_TRIALS):
        tl.time = i * 1e6
        photon = Photon(str(i), tl, encoding_type=time_bin, quantum_state=quantum_state)
        intfm.get(photon)
    tl.time = 0
    tl.run()

    return intfm._receivers[0].log, intfm._receivers[1].log


def test_Interferometer_get():
    # qstate = |e>
    log0, log1 = create_intf(time_bin["bases"][0][0])
    assert abs(len(log0) - len(log1)) / NUM_TRIALS < 0.1
    counter1 = 0
    counter2 = 0

    for time in log0 + log1:
        if time % 1e6 == 0:
            counter1 += 1
        elif time % 1e6 == time_bin["bin_separation"]:
            counter2 += 1
        else:
            assert False

    assert abs(counter1 / (counter1 + counter2) - 0.5) < 0.1

    # qstate = |l>
    log0, log1 = create_intf(time_bin["bases"][0][1])
    assert abs(len(log0) - len(log1)) / NUM_TRIALS < 0.1
    counter1 = 0
    counter2 = 0

    for time in log0 + log1:
        if time % 1e6 == time_bin["bin_separation"]:
            counter1 += 1
        elif time % 1e6 == 2 * time_bin["bin_separation"]:
            counter2 += 1
        else:
            assert False

    assert abs(counter1 / (counter1 + counter2) - 0.5) < 0.1

    # qstate = |e+l>
    log0, log1 = create_intf(time_bin["bases"][1][0])
    assert abs(len(log0) / len(log1)) - 2 < 0.1
    assert len(log0 + log1) / NUM_TRIALS - 3 / 4 < 0.1

    counter1 = 0
    counter2 = 0
    counter3 = 0
    for time in log0:
        if time % 1e6 == 0:
            counter1 += 1
        elif time % 1e6 == time_bin["bin_separation"]:
            counter2 += 1
        elif time % 1e6 == 2 * time_bin["bin_separation"]:
            counter3 += 1
        else:
            assert False

    assert abs(counter1 / counter3 - 1) < 0.1 and abs(counter3 / counter2 - 0.5) < 0.1

    counter1 = 0
    counter2 = 0
    counter3 = 0
    for time in log1:
        if time % 1e6 == 0:
            counter1 += 1
        elif time % 1e6 == time_bin["bin_separation"]:
            counter2 += 1
        elif time % 1e6 == 2 * time_bin["bin_separation"]:
            counter3 += 1
        else:
            assert False

    assert abs(counter1 / counter3 - 1) < 0.1 and counter2 == 0

    # qstate = |e-l>
    log0, log1 = create_intf(time_bin["bases"][1][1])
    assert abs(len(log0) / len(log1)) - 2 < 0.1
    assert len(log0 + log1) / NUM_TRIALS - 3 / 4 < 0.1

    counter1 = 0
    counter2 = 0
    counter3 = 0
    for time in log1:
        if time % 1e6 == 0:
            counter1 += 1
        elif time % 1e6 == time_bin["bin_separation"]:
            counter2 += 1
        elif time % 1e6 == 2 * time_bin["bin_separation"]:
            counter3 += 1
        else:
            assert False

    assert abs(counter1 / counter3 - 1) < 0.1 and abs(counter3 / counter2 - 0.5) < 0.1

    counter1 = 0
    counter2 = 0
    counter3 = 0
    for time in log0:
        if time % 1e6 == 0:
            counter1 += 1
        elif time % 1e6 == time_bin["bin_separation"]:
            counter2 += 1
        elif time % 1e6 == 2 * time_bin["bin_separation"]:
            counter3 += 1
        else:
            assert False

    assert abs(counter1 / counter3 - 1) < 0.1 and counter2 == 0
