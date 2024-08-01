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
from sequence.components.detector import Detector
from sequence.components.photon import Photon   
from sequence.kernel.quantum_manager import QuantumManager
import sequence.components.circuit as Circuit
from qutip import Qobj


MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm

# Definizione della matrice di conversione
def get_conversion_matrix(efficiency: float) -> Qobj:
    custom_gate_matrix = np.array([
        [1, 0, 0, 0],
        [0, math.sqrt(1 - efficiency), math.sqrt(efficiency), 0],
        [0, math.sqrt(efficiency), math.sqrt(1 - efficiency), 0],
        [0, 0, 0, 1]
    ])
    return Qobj(custom_gate_matrix, dims=[[4], [4]])


#Nota: questo è lo stato 1, quindi il trasmone DEVE emettere, se parto dallo sttao 0 NON deve amettere (si può studiare anche questa cosa in fututo)


#Per ora questo protocollo attiva solo il metodo emit proprio del componente trasmone
#si può aggiungere la non idealità interna o esterna (andrebbe studiato questo, va nell'emissione, nell'incremento del contatore del trasduttore o entrambe?)
class EmittingProtocol(Protocol):
    
    "Protocol for emission of single microwave photon by trasmon"

    def __init__(self, own: "Node", name: str, tl: "Timeline", trasmon="Trasmon", transducer="Transducer"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.trasmon = trasmon
        self.transducer = transducer

    def start(self) -> None:
        self.trasmon.emit()

        print(f"Microwave photons emitted by the Trasmon at Tx: {self.trasmon.photon_counter}")
        print(f"Trasmon Quantum state: {self.trasmon.input_quantum_state}")

    def received_message(self, src: str, msg):
        pass



class UpConversionProtocol(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer", node: "Node", trasmon: "Trasmon"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transducer = transducer
        self.trasmon = trasmon
        self.node = node

    def start(self, photon: "Photon") -> None:
        if self.transducer.photon_counter > 0:
            custom_gate = get_conversion_matrix(self.transducer.efficiency)

            trasmon_state_vector = np.array(self.trasmon.input_quantum_state).reshape((4, 1))
            photon_state = Qobj(trasmon_state_vector, dims=[[4], [1]])

            new_photon_state = custom_gate * photon_state
            self.transducer.quantum_state = new_photon_state.full().flatten()

            print(f"Transducer at Tx quantum state: {self.transducer.quantum_state}")

            if random.random() < self.transducer.efficiency:
                photon.wavelength = OPTICAL_WAVELENGTH
                self.transducer._receivers[0].receive_photon(self.node, photon)
                print("Successful up-conversion")
                self.transducer.output_quantum_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]
                print(f"State after successful up-conversion: {self.transducer.output_quantum_state}")
            else:
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[1].get(photon)
                print("FAILED up-conversion")
        else:
            print("No photon to up-convert")

    def received_message(self, src: str, msg):
        pass

class DownConversionProtocol(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer", trasmon: "Trasmon"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transducer = transducer

    def start(self, photon: "Photon") -> None:
        if self.transducer.photon_counter > 0:
            #signfica che il contatore del secondo trasduttore è incrementato, quindi la up_conversion di prima ha avuto successo
            #di conseguenza posso settare quello stato

            transducer_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]
            custom_gate = get_conversion_matrix(self.transducer.efficiency)

            transducer_state_vector = np.array(transducer_state).reshape((4, 1))
            transducer_state = Qobj(transducer_state_vector, dims=[[4], [1]])

            new_transducer_state = custom_gate * transducer_state
            self.transducer.quantum_state = new_transducer_state.full().flatten()

            print(f"Transducer at Rx quantum state: {self.transducer.quantum_state}")

            if random.random() < self.transducer.efficiency:
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[0].receive(photon)
                print("Successful down-conversion")
                self.transducer.output_quantum_state = [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j]
                print(f"State after successful down-conversion: {self.transducer.output_quantum_state}")
            else:
                photon.wavelength = OPTICAL_WAVELENGTH
                self.transducer._receivers[1].get(photon)
                print("FAILED down-conversion")
        else:
            print("No photon to down-convert")

    def received_message(self, src: str, msg):
        pass

class ReceivingProtocol(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", trasmon="Trasmon", transducer="Transducer"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.trasmon = trasmon
        self.transducer = transducer

    def start(self, photon: "Photon") -> None:
        self.trasmon.receive(photon)

    def received_message(self, src: str, msg):
        pass
