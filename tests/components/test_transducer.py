import numpy as np
from sequence.components.transducer import Transducer
from sequence.kernel.timeline import Timeline

def test_Transducer():

    class Owner:
        def __init__(self):
            self.generator = np.random.default_rng(seed=0)

        def get_generator(self):
            return self.generator

    class FakeReceiver:
        pass

    class FakePhoton:
        pass

    tl = Timeline()
    owner = Owner()
    efficiency = 1
    transducer = Transducer(owner, "transducer", tl, efficiency)

    fake_receiver = FakeReceiver()
    transducer.add_outputs([fake_receiver])

    PHOTON_NUMBER = 10
    for _ in range(PHOTON_NUMBER):
        photon = FakePhoton()
        transducer.receive_photon_from_transmon(photon)
    assert transducer.photon_counter == PHOTON_NUMBER

    transducer.photon_counter = 0
    PHOTON_NUMBER = 10
    for _ in range(PHOTON_NUMBER):
        photon = FakePhoton()
        transducer.receive_photon_from_channel(photon)
    assert transducer.photon_counter == PHOTON_NUMBER
