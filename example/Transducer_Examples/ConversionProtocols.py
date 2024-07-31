import random
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

MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm


#Nota: questo è lo stato 1, quindi il trasmone DEVE emettere, se parto dallo sttao 0 NON deve amettere (si può studiare anche questa cosa in fututo)


#si può aggiungere la non idealità interna o esterna (andrebbe studiato questo, va nell'emissione, nell'incremento del contatore del trasduttore o entrambe?)
class EmittingProtocol(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", trasmon="Trasmon", transducer="Transducer"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.trasmon = trasmon
        self.transducer = transducer

    def start(self) -> None:
         
        self.trasmon.emit()

        
        #print di controllo

        print(f"Microwave photons emitted by the Trasmon at Tx: {self.trasmon.photon_counter}") 
        # #questo è per verificare che il contatore del trasmone sia stato incrementato di un fotone, se è stato incrementato significa che ha emesso

        #print(f"Transducer Photon counter: {self.transducer.photon_counter}") #questo può servire s evuoi in futuro aggiungere non idealità tra il trasmone e il transducer (per ora supponiamo emissione non ideale ma collegamento ideale)

        print(f"Trasmon Quantum state: {self.trasmon.input_quantum_state}") #questo non ci deve essere sempre
       
        #print(f"Trasmon Quantum state: {self.trasmon.input_quantum_state}") #questo non ci deve essere sempre
        #print(f"Trasmon-Photon Wavelength: {self.trasmon.wavelength}") #come li prendo dal new photon? vedi CHGP #neanche questo
       

    def received_message(self, src: str, msg):
        pass



#nota per questi protocolli: il detector della prima condizione è quello che identifica la conversione AVVENUTA :)


class UpConversionProtocol(Protocol):
    "Questo protocollo è per la cup-comversion dei fotoni. "
    "Se il trasduttore ha ricevuto un fotone dal trasmone (il suo contatore è maggiore di 0), allora il fotone può essere up-convertito con una certa probabilità che dipende dell'efficienza del trasdtuttore stesso."
    "Se la up-convertion è avvenuta, il fotone up-convertito (viene cambiata la sua wavelenght) e viene inviato al nodo destinatario tramite il metodo receive_photon ."
    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer:"Transducer", node: "Node"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl  
        self.transducer = transducer 
        self.node = node

    def start(self, photon: "Photon") -> None:
        if self.transducer.photon_counter > 0:
            if random.random() < self.transducer.efficiency:
                photon.wavelength = OPTICAL_WAVELENGTH  
                up_conversion_state = (0.0 + 0.0j, math.sqrt(self.transducer.efficiency) + 0.0j, math.sqrt(1-self.transducer.efficiency) + 0.0j,0.0 + 0.0j)
                photon.quantum_state = up_conversion_state
                self.transducer._receivers[0].receive_photon(self.node, photon)
                print("Successful up-conversion")
                print(f"Photon state after up-conversion: {photon.quantum_state}")
            else:
                photon.wavelength = MICROWAVE_WAVELENGTH 
                self.transducer._receivers[1].get(photon)
                print("FAILED up-conversion")
        else:
            print("No photon to up-convert")
    def received_message(self, src: str, msg):
        pass


class DownConversionProtocol(Protocol):
    def __init__(self, own: "Node", name: str,  tl: "Timeline", transducer: "Transducer"):
        super().__init__(own, name)    
        self.owner = own
        self.name = name
        self.tl = tl  
        self.transducer = transducer  

    def start(self, photon: "Photon") -> None: 
        if self.transducer.photon_counter > 0:
            if random.random() < self.transducer.efficiency:
                down_conversion_state = (0.0 + 0.0j, math.sqrt(1-self.transducer.efficiency) + 0.0j, math.sqrt(self.transducer.efficiency) + 0.0j,0.0 + 0.0j)
                photon.quantum_state = down_conversion_state
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[0].receive(photon) 
                print("Successful down-conversion")
                print(f"Photon state after down-conversion: {photon.quantum_state}")
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

    def start(self,photon: "Photon") -> None:
         
        self.trasmon.receive(photon)

        
        #print di controllo

       # print(f"Trasmon Photon counter: {self.trasmon.photon_counter}")
        #print(f"Transducer Photon counter: {self.transducer.photon_counter}")
        #print(f"Trasmon Quantum state: {self.trasmon.quantum_state}")
        #print(f"Trasmon-Photon Wavelength: {self.trasmon.wavelength}") #come li prendo dal new photon? vedi CHGP
       
        #aggiungi non idealità

    def received_message(self, src: str, msg):
        pass
