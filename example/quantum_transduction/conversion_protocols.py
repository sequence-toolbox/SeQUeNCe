"""Protocols for Quantum Transduction via Direct Conversion

NOTE: work in progress
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
from sequence.constants import KET0, KET1
from sequence.components.photon import Photon   
from qutip import Qobj


MICROWAVE_WAVELENGTH = 999308  # nm
OPTICAL_WAVELENGTH = 1550  # nm


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
        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.transmon = transmon
        self.transducer = transducer

    def start(self) -> None:

        self.transmon.get()

        if self.transmon.photons_quantum_state[0] == KET1:
            if random.random() < self.transmon.efficiency:
                self.transmon._receivers[0].receive_photon_from_transmon(self.transmon.new_photon0) 
                self.transmon.photon_counter += 1 
            else:
                pass
        else:
            print("The transmon is in the state 00, or 01, it doesn't emit microwave photons")
        
        print(f"Microwave photons emitted by the Transmon at Tx: {self.transmon.photon_counter}")

    def received_message(self, src: str, msg):
        pass


class UpConversionProtocol(Protocol):
    """Protocol for Up-conversion of an input microwave photon into an output optical photon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transducer (Transducer): the transducer component
        node (Node): the receiver node (where DownConversionProtocol runs).
            NOTE this is an error! node's typing should be a str, instead of Node
        transmon (Transmon): the transmon component
    """

    def __init__(self, owner: Node, name: str, tl: Timeline, transducer: Transducer, node: Node, transmon: Transmon):
        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.transducer = transducer
        self.transmon = transmon
        self.node = node

    def start(self, photon: Photon) -> None:
        """start the protocol  

        NOTE (caitao, 12/21/2024): this start() method should be empty. 
             The content of this function should be at a new convert() method that receives photons from the transducer.

        Args:
            photon (Photon): photon from arrived at the transducer from the transmon
        """
        if self.transducer.photon_counter > 0:   # NOTE shouldn't use this photon_counter to determine
            custom_gate = get_conversion_matrix(self.transducer.efficiency)

            transmon_state_vector = np.array(self.transmon.input_quantum_state).reshape((4, 1))
            photon_state = Qobj(transmon_state_vector, dims=[[4], [1]])

            new_photon_state = custom_gate * photon_state
            self.transducer.quantum_state = new_photon_state.full().flatten()

            print(f"Transducer at Tx quantum state: {self.transducer.quantum_state}")

            if random.random() < self.transducer.efficiency:
                photon.wavelength = OPTICAL_WAVELENGTH
                self.transducer._receivers[0].receive_photon(self.node, photon)  # NOTE the receiver should be the quantum channel
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
    """Protocol for Down-conversion of an input optical photon into an output microwave photon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transducer (Transducer): the transducer component
    """

    def __init__(self, owner: "Node", name: str, tl: "Timeline", transducer: "Transducer", transmon: "Transmon"):
        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.transducer = transducer

    def start(self, photon: "Photon") -> None:
        """start the protocol
            
            NOTE (caitao, 12/21/2024): this start() method should be empty. 
                 The content of this function should be at a new convert() method that receives photons from the transducer
        Args:
            photon (Photon): the photon received at the transducer from the quantum channel
        """
        if self.transducer.photon_counter > 0:   # NOTE shouldn't use this photon_counter to determine

            transducer_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]  # NOTE Why is this the transducer's state 
            custom_gate = get_conversion_matrix(self.transducer.efficiency)

            transducer_state_vector = np.array(transducer_state).reshape((4, 1))
            transducer_state = Qobj(transducer_state_vector, dims=[[4], [1]])

            new_transducer_state = custom_gate * transducer_state
            self.transducer.quantum_state = new_transducer_state.full().flatten()

            print(f"Transducer at Rx quantum state: {self.transducer.quantum_state}")

            if random.random() < self.transducer.efficiency:
                photon.wavelength = MICROWAVE_WAVELENGTH
                self.transducer._receivers[0].receive_photon_from_transducer(photon)
                print("Successful down-conversion")
                self.transducer.output_quantum_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]
                print(f"State after successful down-conversion: {self.transducer.output_quantum_state}")
            else:
                photon.wavelength = OPTICAL_WAVELENGTH
                self.transducer._receivers[1].get(photon)
                print("FAILED down-conversion")
        else:
            print("No photon to down-convert")

    def received_message(self, src: str, msg):
        pass

