"""Protocols for Quantum Transduction via Entanglement Swapping

NOTE: work in progress
"""
import random
from sequence.kernel.timeline import Timeline
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.photon import Photon
from sequence.components.photon import Photon   
from sequence.components.beam_splitter import FockBeamSplitter2
from sequence.components.transducer import Transducer
from sequence.components.transmon import Transmon

MICROWAVE_WAVELENGTH = 999308  # nm
OPTICAL_WAVELENGTH = 1550  # nm


class EmittingProtocol(Protocol):

    """Protocol for emission of single microwave photon by transmon"""

    def __init__(self, own: Node, name: str, tl: Timeline, transmon: Transmon, transducer: Transducer):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transmon = transmon
        self.transducer = transducer

    def start(self) -> None:

        self.transducer.photon_counter += 1 
        print(f"Microwave photons emitted by {self.name}: {self.transducer.photon_counter}")

    def received_message(self, src: str, msg):
        pass


class UpConversionProtocol(Protocol):

    """Convert Microwave photon into optical photon."""

    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer", node: "Node", transmon: "Transmon"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transducer = transducer
        self.transmon = transmon
        self.node = node

    def start(self, photon: Photon) -> None:  

        if self.transducer.photon_counter > 0:

            if random.random() < self.transducer.efficiency:
                self.transducer._receivers[0].receive_photon(photon, [self.node.name])
                print(f"{self.name}: Successful up-conversion")
            else:
                self.transducer._receivers[1].receive_photon_from_transducer(photon)
                print(f"{self.name}: FAILED up-conversion")
        else:
            print(f"{self.name}: No photon to up-convert")

    def received_message(self, src: str, msg):
        pass


class Swapping(Protocol):

    """Entanglement swapping in the middle."""
    
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

    def start(self, photon: Photon) -> None:

        receivers = self.FockBS._receivers
        photon_count = self.FockBS.photon_counter

        if photon_count == 1:
            selected_receiver = random.choice(receivers)
            selected_receiver.get(photon)
            selected_receiver.get_2(photon) 

        elif photon_count == 2:
            selected_receiver = random.choice(receivers)
            selected_receiver.get(photon)
            selected_receiver.get(photon)

            selected_receiver.get_2(photon) 
            selected_receiver.get_2(photon)

    def received_message(self, src: str, msg):
        pass


class Measure(Protocol):
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

        self.detector_photon_counter_real = 0
        self.spd_real = 0

        self.detector_photon_counter_ideal = 0
        self.spd_ideal = 0

    def start(self, photon: Photon) -> None:

        if self.FockBS._receivers[0].photon_counter == 1 or self.FockBS._receivers[1].photon_counter == 1:
            self.detector_photon_counter_real += 1

        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.spd_real += 1

        if self.FockBS._receivers[0].photon_counter2 == 1 or self.FockBS._receivers[1].photon_counter2 == 1:
            self.detector_photon_counter_ideal += 1

        if self.FockBS._receivers[0].photon_counter2 >= 1 or self.FockBS._receivers[1].photon_counter2 >= 1:
            self.spd_ideal += 1

    def get_detector_photon_counter_real(self):
        return self.detector_photon_counter_real

    def get_spd_real(self):
        return self.spd_real
    
    def get_detector_photon_counter_ideal(self):
        return self.detector_photon_counter_ideal

    def get_spd_ideal(self):
        return self.spd_ideal

    def received_message(self, src: str, msg):
        pass


class SwappingIdeal(Protocol):
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
    
    def start(self, photon: Photon) -> None:

        receivers = self.FockBS._receivers
        photon_count = self.FockBS.photon_counter

        real_efficiency_0 = self.FockBS._receivers[0].efficiency
        real_efficiency_1 = self.FockBS._receivers[1].efficiency

        self.FockBS._receivers[0].set_efficiency(1) 
        self.FockBS._receivers[1].set_efficiency(1)
            
        if photon_count == 1: 
            selected_receiver = random.choice(receivers)
            selected_receiver.get_2(photon)

        elif photon_count == 2:
            selected_receiver = random.choice(receivers)
            selected_receiver.get_2(photon)
            selected_receiver.get_2(photon)

        self.FockBS._receivers[0].set_efficiency(real_efficiency_0)
        self.FockBS._receivers[1].set_efficiency(real_efficiency_1)

    def received_message(self, src: str, msg):
        pass


class MeasureIdeal(Protocol):
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

        self.detector_photon_counter_ideal = 0
        self.spd_ideal = 0

        self.detector_photon_counter_real = 0 
        self.spd_real = 0

    def start(self, photon: Photon) -> None:
        
        if self.FockBS._receivers[0].photon_counter2 == 1 or self.FockBS._receivers[1].photon_counter2 == 1:
            self.detector_photon_counter_real += 1
        
        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.spd_real += 1
      
        print(f"Ideal detector photon counter: {self.detector_photon_counter_ideal}")
        print(f"Ideal SPD: {self.spd_ideal}")

        print(f"Detector photon counter with eta NOT 1 : {self.entanglement_count_real}") 
        print(f"SPD with eta NOT 1: {self.spd_real}")
        
    def received_message(self, src: str, msg):
        pass
