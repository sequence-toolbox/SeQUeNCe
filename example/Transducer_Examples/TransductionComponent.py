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



class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1



class Trasmon(Entity):
    def __init__(self, owner: "Node", name: str, timeline: "Timeline", wavelength: List[int], photon_counter: int, photons_quantum_state: List[tuple], efficiency=1):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.wavelength = wavelength
        self.photon_counter = photon_counter #il photon counter fa riferimento ai fotoni alle microonde (non quelli ottici)
        self.photons_quantum_state = photons_quantum_state
        self.efficiency=efficiency #per modellare eventuali non idealità

    def init(self):
        pass

    def add_output(self, outputs: List):
        for i in outputs:
            self.add_receiver(i)

    def emit(self) -> None:
        
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
        #print(input_quantum_state)
        #controllo dello stato di input del trasmone
        
        #aggiunta di non idealità di emissione (sto supponendo di voler emmetere sempre per che lo stato che voglio mandare è 1)
        if random.random() < self.efficiency:
            self._receivers[0].receive_photon_from_trasmon(input_photons)
            #qui con il quantum manager dovresti mandargli lo stato
            self.photon_counter += 1 #utile se vuoi aggiungere non idealità
        else:
            pass
    
    def receive(self, photon: "Photon") -> None:
        self.photon_counter += 1
        #docrebbe anche riceverlo in qualche modo ma è ok
        
        
class Transducer(Entity):
    def __init__(self, owner: "Node", name: str, timeline: "Timeline", efficiency=1, photon_counter=int, quantum_state=tuple):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = photon_counter
        self.quantum_state = quantum_state

    def init(self):
        assert len(self._receivers) == 2

    def add_output(self, outputs: List):
        for i in outputs:
            self.add_receiver(i)
    
    def receive_photon_from_trasmon(self, photon: "Photon") -> None:
        self.photon_counter += 1 #in questo caso il contatore indica che ha ricevuto un fotone alle microonde

    def receive_photon_from_channel(self, photon: "Photon") -> None:
        self.photon_counter += 1 #in questo caso il contatore indica che ha ricevuto un fotone ottico
        #capire come diffenrenziare questi due casi

    def microwave_initialization(self, photon: "Photon") -> None:
        self.photon_counter += 1
    #questa può essere utile per la EQT



class FockDetector(Detector):
    def __init__(self, name: str, timeline: "Timeline", efficiency=1, wavelength=int, encoding_type=fock):
        super().__init__(name, timeline, efficiency)
        self.name = name
        self.photon_counter = 0
        self.wavelength = wavelength
        self.encoding_type = encoding_type
        self.timeline = timeline
        self.efficiency = efficiency
    
    def init(self):
        pass

    def get(self, photon=None, **kwargs) -> None:
        if random.random() < self.efficiency:
            self.photon_counter += 1
    
    def receive_photon(self, src: str, photon: "Photon") -> None:
        if photon.wavelength == self.wavelength:
            self.get(photon)
        else:
            pass


