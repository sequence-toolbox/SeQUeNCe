import random
import numpy as np
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.light_source import LightSource
from sequence.utils.encoding import absorptive, single_atom
from sequence.components.photon import Photon
from sequence.kernel.entity import Entity
from typing import List, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
from sequence.components.memory import Memory
from sequence.utils.encoding import fock
import math
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import sequence.utils.log as log
import matplotlib.pyplot as plt
from sequence.components.detector import Detector
from typing import List
import sequence.components.circuit as Circuit
from qutip import Qobj

ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 

class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1



class Transmon(Entity):

    """Class modeling a transmon qubit.

    The Transmon class can be configured to emit microwave photons.

    """

    def __init__(self, owner: "Node", name: str, timeline: "Timeline", wavelength: List[int], photon_counter: int, photons_quantum_state: List[tuple], efficiency=1):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.wavelength = wavelength
        self.photon_counter = photon_counter 
        self.photons_quantum_state = photons_quantum_state 
        self.efficiency=efficiency 

    def init(self):
        pass

    def add_output(self, outputs: List):
        for i in outputs:
            self.add_receiver(i)

    def get(self) -> None:

        new_photon0 = Photon(name=self.name,
                            timeline=self.timeline,
                            wavelength=self.wavelength[0],
                            quantum_state=self.photons_quantum_state[0])
                            
        new_photon1 = Photon(name=self.name,
                            timeline=self.timeline,
                            wavelength=self.wavelength[1],
                            quantum_state=self.photons_quantum_state[1]
                            )
                            
        input_photons = [new_photon0, new_photon1]
        input_quantum_state= np.kron(self.photons_quantum_state[0], self.photons_quantum_state[1])
        self.input_quantum_state = input_quantum_state 
        self.new_photon0=new_photon0
        self.new_photon1=new_photon1
    
    def receive_photon_from_transducer(self, photon: "Photon") -> None:
        self.photon_counter += 1

    def receive_photon(self, photon: "Photon") -> None:
        self.photon_counter += 1
        
        
class Transducer(Entity):

    """Class modeling a transducer.
    A transducer can operate in two modes: up-conversion and down-conversion.
    In up-conversion it can convert microwave photons to optical photons.
    In down-conversion it can convert optical photons to microwave photons.

    """
    def __init__(self, owner: "Node", name: str, timeline: "Timeline", efficiency=1, photon_counter=int):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = photon_counter
        

    def init(self):
        assert len(self._receivers) == 2

    def add_output(self, outputs: List):
        for i in outputs:
            self.add_receiver(i)
    
    def receive_photon_from_transmon(self, photon: "Photon") -> None:
        self.photon_counter += 1 

    def receive_photon_from_channel(self, photon: "Photon") -> None:
        self.photon_counter += 1




class FockDetector(Detector):

    """Class modeling a Fock detector.
    A Fock detector can detect the number of photons in a given mode.
    """

    def __init__(self, name: str, timeline: "Timeline", efficiency=1, wavelength=int, encoding_type=fock):
        super().__init__(name, timeline, efficiency)
        self.name = name
        self.photon_counter = 0
        self.photon_counter2 = 0
        self.wavelength = wavelength
        self.encoding_type = encoding_type
        self.timeline = timeline
        self.efficiency = efficiency
    
    def init(self):
        pass

    def get(self, photon=None, **kwargs) -> None:
        if random.random() < self.efficiency:
            self.photon_counter += 1

    def get_2(self, photon=None, **kwargs) -> None:
            self.photon_counter2 += 1
    
    def set_efficiency(self, efficiency):
        self.efficiency = efficiency


    def receive_photon(self, src: str, photon: "Photon") -> None:
        if photon.wavelength == self.wavelength:
            self.get(photon)
        else:
            pass



class FockBeamSplitter(Entity):

    """Class modeling a Fock beam splitter.
    A Fock beam splitter can send a single photon randomly in one of its ports.

    """
    def __init__(self, name: str, owner: "Node", timeline: "Timeline", efficiency:int, photon_counter:int, src_list: List[str]):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = photon_counter
        
    def init(self):
        assert len(self._receivers) == 2

    def receive_photon_from_scr(self, photon: "Photon", source: List[str]) -> None:
        self.photon_counter += 1

    def add_output(self, outputs: List):
        for i in outputs:
            self.add_receiver(i)

    def send_photon(self, receiver: "Entity", photon: "Photon") -> None:
        receiver.get(self.name, photon)


