"""Model for a transducer.

See https://arxiv.org/abs/2411.11377, Simulation of Quantum Transduction Strategies for Quantum Networks
"""

from typing import List
import random
import math
import numpy as np
from qutip import Qobj
from ..kernel.entity import Entity
from ..kernel.timeline import Timeline
from ..topology.node import Node
from ..components.photon import Photon
from ..protocol import Protocol

MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH   = 1550   # nm



class Transducer(Entity):
    """Class modeling a transducer.

    A transducer can operate in two modes: up-conversion and down-conversion.
    In up-conversion it can convert microwave photons to optical photons.
    In down-conversion it can convert optical photons to microwave photons.

    Attributes:
        owner (Node): the entity that owns or aggregates the current component
        name (str): the name of the transducer
        timeline (Timeline): the simulation timeline
        efficiency (float): the efficiency of the transducer
        photon_counter (int): photon counter
        up_conversion_protocol (UpConversionProtocol):       up convert microwave to photon
        down_conversion_protocol (DownConversionProtocol): down convert photon to microwave
    """
    def __init__(self, owner: Node, name: str, timeline: Timeline, efficiency: float = 1):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = 0
        self.up_conversion_protocol = None
        self.down_conversion_protocol = None 
        

    def init(self):
        pass


    def add_outputs(self, outputs: List):
        """Add outputs, i.e., receivers"""
        for i in outputs:
            self.add_receiver(i)
    

    def receive_photon_from_transmon(self, photon: Photon) -> None:
        """Receive a photon from the transmon and call the Up_Conversion protocol
        """
        self.up_conversion_protocol.convert(photon)
       
        
    def get(self, photon) -> None:
        """The optical photon reaches the destination
        """
        self.photon_counter += 1
        self.down_conversion_protocol.convert(photon)



def get_conversion_matrix(efficiency: float) -> Qobj:
    """
    Args:
        efficiency (float): transducer efficiency
    """
    custom_gate_matrix = np.array([
        [1, 0, 0, 0],
        [0, math.sqrt(1 - efficiency), math.sqrt(efficiency), 0],
        [0, math.sqrt(efficiency), math.sqrt(1 - efficiency), 0],
        [0, 0, 0, 1]
    ])
    return Qobj(custom_gate_matrix, dims=[[4], [4]])



class UpConversionProtocol(Protocol):
    """Protocol for Up-conversion of an input microwave photon into an output optical photon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transducer (Transducer): the transducer component
    """

    def __init__(self, owner: Node, name: str, tl: Timeline, transducer: Transducer):

        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.transducer = transducer

    def start(self) -> None:
        """start the protocol  
        """
        pass

    def convert(self, photon: Photon) -> None:
        """receives

        Args:
            photon (Photon): photon from arrived at the transducer from the transmon
        """
        print(f"Transducer first receiver: {self.transducer._receivers[0]}")
        print(f"Transducer second receiver: {self.transducer._receivers[1]}")

        if random.random() < self.transducer.efficiency:
            photon.wavelength = OPTICAL_WAVELENGTH
            print("Successful up-conversion")
            print(f"The photon is: {photon} with wavelength: {photon.wavelength} at time {self.tl.now()}")
            self.transducer._receivers[0].transmit(photon)
        else:
            photon.wavelength = MICROWAVE_WAVELENGTH
            self.transducer._receivers[1].get(photon)
            print("FAILED up-conversion")

    def received_message(self, src: str, msg):
        pass


class DownConversionProtocol(Protocol):
    """Protocol for Down-conversion of an input optical photon into an output microwave photon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transducer (Transducer): the transducer component
    """

    def __init__(self, owner: "Node", name: str, tl: "Timeline", transducer: "Transducer"):
        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.transducer = transducer

    def start(self) -> None:
        """start the protocol
            
        Args:
            photon (Photon): the photon received at the transducer from the quantum channel
        """

    def convert(self, photon: Photon) -> None:
        """Receives photons from the transducer
        """
        print(f"PHOTON IS: {photon}")
        if random.random() < self.transducer.efficiency:
            photon.wavelength = MICROWAVE_WAVELENGTH
            print("Successful down-conversion")
            print(f"The photon is: {photon} with wavelength: {photon.wavelength}")
            print(f"Transducer receiver: {self.transducer._receivers[0]}")
            self.transducer._receivers[0].get(photon)
        else:
            photon.wavelength = OPTICAL_WAVELENGTH
            self.transducer._receivers[1].get(photon)
            print("FAILED down-conversion")
            print(f"Transducer receiver: {self.transducer._receivers[1]}")

    def received_message(self, src: str, msg):
        pass
