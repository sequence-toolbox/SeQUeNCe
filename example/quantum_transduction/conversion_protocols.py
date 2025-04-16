"""Protocols for Quantum Transduction via Direct Conversion
"""

import random
import numpy as np
from sequence.kernel.timeline import Timeline
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.photon import Photon
import math
from sequence.components.transducer import Transducer
from sequence.components.transmon import Transmon
from sequence.constants import KET1
from qutip import Qobj


MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm

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


class EmittingProtocol(Protocol):
    """Protocol for emission of single microwave photon by transmon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transducer (Transducer): the transducer component
        transmon (Transmon): the transmon component
    """

    def __init__(self, owner: "Node", name: str, tl: Timeline, transmon: Transmon, transducer: Transducer):
    #def __init__(self, owner: "Node", name: str, tl: Timeline, transducer: Transducer):

        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.transmon = transmon
        self.transducer = transducer

    def start(self):
        print(f"EmittingProtocol started for {self.owner.name} at time {self.tl.now()}")
        photon = self.transmon.generation()
        print(f"Photon created: {photon}, Name: {photon.name}, Wavelength: {photon.wavelength}")
        print(f"Transmon at Tx quantum state: {self.transmon.input_quantum_state} of {self.owner.name}")

        if self.transmon.photons_quantum_state[0] == KET1:
            if random.random() < self.transmon.efficiency:
                print(f"Transmon receiver " + str(self.transmon._receivers[0]))
                self.transmon._receivers[0].receive_photon_from_transmon(photon)
            else:
                print("Photon emission failed due to transmon efficiency")
        else:
            print("The transmon is in the state 00, or 01, it doesn't emit microwave photons")
        
    def received_message(self, src: str, msg):
        pass


class UpConversionProtocol(Protocol):
    """Protocol for Up-conversion of an input microwave photon into an output optical photon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transducer (Transducer): the transducer component
        node (Node): the receiver node (where DownConversionProtocol runs) -- NOTE this is an error! node's typing should be a str, instead of Node
        transmon (Transmon): the transmon component
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
            
            NOTE (caitao, 12/21/2024): this start() method should be empty. 
                 The content of this function should be at a new convert() method that receives photons from the from the transducer
        Args:
            photon (Photon): the photon received at the transducer from the quantum channel
        """

    def convert(self, photon: Photon) -> None:
        """Receives photons from the transducer"""
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