import numpy as np
from sequence.components.transmon import Transmon
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.constants import KET0, KET1


def test_Transmon():

    class Owner:
        def __init__(self):
            self.generator = np.random.default_rng(seed=0)

        def get_generator(self):
            return self.generator

    class FakeReceiver:
        pass

    class FakePhoton:
        pass

    MICROWAVE_WAVELENGTH = 999308 # nm
    OPTICAL_WAVELENGTH = 1550 # nm
    state_list= [KET1, KET0]
    TRANSMON_EFFICIENCY = 1

    tl = Timeline()
    owner = Owner()
    fake_receiver = FakeReceiver()
    wavelengths = [MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH]
    transmon = Transmon('transmon', owner, tl, wavelengths=wavelengths, photon_counter=0, 
                        photons_quantum_state=state_list, efficiency=TRANSMON_EFFICIENCY)
    
    transmon.add_outputs([fake_receiver])
    transmon.get()
    expect = [0, 0, 1, 0]
    assert np.array_equal(transmon.input_quantum_state, expect)

    NUM_PHOTONS = 10
    for _ in range(NUM_PHOTONS):
        fake_photon = FakePhoton
        transmon.receive_photon_from_transducer(fake_photon)
    assert transmon.photon_counter == NUM_PHOTONS
