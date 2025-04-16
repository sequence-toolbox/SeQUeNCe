import numpy as np
from sequence.components.photon import Photon
from sequence.components.transducer import Transducer, UpConversionProtocol, DownConversionProtocol
from sequence.kernel.timeline import Timeline



def test_Transducer():

    class FakeNode:
        def __init__(self):
            self.name = 'fake_node'
            self.generator = np.random.default_rng(seed=0)

        def get_generator(self):
            return self.generator


    class FakePhoton:
        pass


    class FakeUpConversionProtocol(UpConversionProtocol):
        def __init__(self, owner: FakeNode, name: str, tl: Timeline, transducer: Transducer):
            super().__init__(owner, name, tl, transducer)

        def convert(self, photon: FakePhoton):
            pass


    class FakeDownConversionProtocol(DownConversionProtocol):
        def __init__(self, owner: FakeNode, name: str, tl: Timeline, transducer: Transducer):
            super().__init__(owner, name, tl, transducer)

        def convert(self, photon: FakePhoton):
            pass


    tl = Timeline()
    node = FakeNode()
    efficiency = 1
    transducer = Transducer(node, "transducer", tl, efficiency)
    transducer.up_conversion_protocol   = FakeUpConversionProtocol(node, f'{node.name}.up_convertion_protocol', tl, transducer)
    transducer.down_conversion_protocol = FakeDownConversionProtocol(node, f'{node.name}.down_convertion_protocol', tl, transducer)

    PHOTON_NUMBER = 10
    transducer.photon_counter = 0
    for _ in range(PHOTON_NUMBER):
        photon = FakePhoton()
        transducer.get(photon)
    assert transducer.photon_counter == PHOTON_NUMBER
