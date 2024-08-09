import random
import numpy as np
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.light_source import LightSource
from sequence.components.photon import Photon
from sequence.kernel.entity import Entity
from sequence.components.memory import Memory
from sequence.utils.encoding import fock
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import sequence.utils.log as log
import matplotlib.pyplot as plt
from example.Transducer_Examples.TransductionComponent import Transducer
from example.Transducer_Examples.TransductionComponent import FockDetector
from example.Transducer_Examples.TransductionComponent import Trasmon
from example.Transducer_Examples.TransductionComponent import Counter
from example.Transducer_Examples.TransductionComponent import FockBeamSplitter

from sequence.components.detector import Detector
from sequence.components.photon import Photon   
from sequence.kernel.quantum_manager import QuantumManager
import sequence.components.circuit as Circuit
from qutip import Qobj




ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 

MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm



class UpConversionProtocolEntangle(Protocol): 
    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer", node: "Node"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transducer = transducer
        self.node = node

    def start(self, photon: "Photon") -> None:
            if random.random() < self.transducer.efficiency:
                photon.wavelength = OPTICAL_WAVELENGTH
                self.transducer._receivers[0].receive_photon(self.node, photon)
                print("Successful up-conversion")

                self.transducer.output_quantum_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]
              
            else:
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[1].receive_photon(photon)
                print("FAILED up-conversion")
        

    def received_message(self, src: str, msg):
        pass



class Swapping(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

       
    def start(self, photon: "Photon") -> None:

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
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

        self.detector_photon_counter_real = 0
        self.spd_real= 0  

        self.detector_photon_counter_ideal = 0
        self.spd_ideal= 0 


    def start(self, photon: "Photon") -> None:

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
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
    
    def start(self, photon: "Photon") -> None:

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




class MeasureIdeal(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

        self.detector_photon_counter_ideal = 0
        self.spd_ideal= 0  


        self.detector_photon_counter_real = 0 
        self.spd_real= 0  

    def start(self, photon: "Photon") -> None:
        
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