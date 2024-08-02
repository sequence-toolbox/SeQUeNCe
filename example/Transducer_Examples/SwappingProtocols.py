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

class UpConversionProtocolEntangle(Protocol): #versione per entanglement swapping, semplificata senza trasmone 
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
                #il nodo2 (e quindi il trasduttore) riceve il fotone ottico e incrementa il suo contatore
                print("Successful up-conversion")
                self.transducer.output_quantum_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]
                print(f"State after successful up-conversion: {self.transducer.output_quantum_state}")
            else:
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[1].get(photon)
                print("FAILED up-conversion")
        

    def received_message(self, src: str, msg):
        pass


class SwappingProtocol(Protocol): #versione per entanglement swapping, semplificata senza trasmone 
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter", node: "Node"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
        self.node = node

    def start(self, photon: "Photon") -> None:
        import random

class SwappingMeasure(Protocol): 
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter", node: "Node"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
        self.node = node

    def start(self, photon: "Photon") -> None:
        if self.FockBS.photon_counter > 0:
            receivers = self.FockBS._receivers()  
            for _ in range(self.FockBS.photon_counter):
                selected_receiver = random.choice(receivers)
                self.send_photon(selected_receiver, photon)  # Supponiamo che tu abbia un metodo per inviare i fotoni

            # Reset the photon counter after processing
            self.FockBS.photon_counter = 0

    def received_message(self, src: str, msg):
        pass

            

    def received_message(self, src: str, msg):
        pass