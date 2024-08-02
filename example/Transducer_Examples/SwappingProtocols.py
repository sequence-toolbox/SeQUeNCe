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
                #print(f"State after successful up-conversion: {self.transducer.output_quantum_state}")
                #print di controllo
            else:
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[1].get(photon)
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
        elif photon_count == 2:
            selected_receiver = random.choice(receivers)
            selected_receiver.get(photon)
            selected_receiver.get(photon)  # Invia entrambi i fotoni allo stesso ricevitore
    
    def received_message(self, src: str, msg):
        pass





class Measure(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", FockBS: "FockBeamSplitter", entanglement_count: int):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
        self.entanglement_count = 0
        self.entanglement_count_spd = 0  # nuovo contatore
        self.entanglement_count_real = 0  # contatore reale
        self.entanglement_count_spd_real = 0  # nuovo contatore reale

    def start(self, photon: "Photon") -> None:
        # Efficienza reale dei ricevitori, così da richiamarla dopo più facilmente
        real_efficiency_0 = self.FockBS._receivers[0].efficiency
        real_efficiency_1 = self.FockBS._receivers[1].efficiency

        # Temporaneamente impostiamo l'efficienza a 1 per i contatori ideali
        self.FockBS._receivers[0].set_efficiency(1)
        self.FockBS._receivers[1].set_efficiency(1)
        print(f"Efficiency detecor 1: {real_efficiency_0}")
        print(f"Efficiency detector 2: {real_efficiency_1}")
        print(f"Efficiency detector 1 (ideal): {self.FockBS._receivers[0].efficiency}")
        print(f"Efficiency detector 2 (ideal): {self.FockBS._receivers[1].efficiency}")

        # Incrementa entanglement_count e entanglement_count_spd per efficienza ideale
        if self.FockBS._receivers[0].photon_counter == 1 or self.FockBS._receivers[1].photon_counter == 1:
            self.entanglement_count += 1
        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.entanglement_count_spd += 1

        # Ripristina l'efficienza reale
        self.FockBS._receivers[0].set_efficiency(real_efficiency_0)
        self.FockBS._receivers[1].set_efficiency(real_efficiency_1)

        print(f"Efficiency detector 1 (real): {self.FockBS._receivers[0].efficiency}")
        print(f"Efficiency detector 2 (real): {self.FockBS._receivers[1].efficiency}")

        # Incrementa entanglement_count_real e entanglement_count_spd_real per efficienza reale
        if self.FockBS._receivers[0].photon_counter == 1 or self.FockBS._receivers[1].photon_counter == 1:
            self.entanglement_count_real += 1
        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.entanglement_count_spd_real += 1

        print(f"Entanglement count (ideal): {self.entanglement_count}")
        print(f"Entanglement count SPD (ideal): {self.entanglement_count_spd}")
        print(f"Entanglement count (real): {self.entanglement_count_real}")
        print(f"Entanglement count SPD (real): {self.entanglement_count_spd_real}")

    def received_message(self, src: str, msg):
        pass
