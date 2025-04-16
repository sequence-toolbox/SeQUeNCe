import numpy as np
from sequence.components.transmon import Transmon
from sequence.kernel.timeline import Timeline
from sequence.constants import KET0, KET1


def test_Transmon():

    class FakeNode:
        def __init__(self):
            self.name = 'FakeNode'
            self.generator = np.random.default_rng(seed=0)

        def get_generator(self):
            return self.generator


    class FakePhoton:
        pass


    MICROWAVE_WAVELENGTH = 999308 # nm
    OPTICAL_WAVELENGTH = 1550 # nm
    state_list= [KET1, KET0]
    TRANSMON_EFFICIENCY = 1

    tl = Timeline()
    node = FakeNode()
    wavelengths = [MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH]
    transmon = Transmon(node, f'{node.name}.transmon', tl, wavelengths=wavelengths, photon_counter=0, 
                        photons_quantum_state=state_list, efficiency=TRANSMON_EFFICIENCY)
    
    expect = [0, 0, 1, 0]
    _ = transmon.generation()
    assert np.array_equal(transmon.input_quantum_state, expect)

    NUM_PHOTONS = 10
    for _ in range(NUM_PHOTONS):
        photon = FakePhoton()
        transmon.receive_photon(photon)
    assert transmon.photon_counter == NUM_PHOTONS
