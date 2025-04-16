"""Model for a transmon.

See https://arxiv.org/abs/2411.11377, Simulation of Quantum Transduction Strategies for Quantum Networks
"""

import random
from typing import List
import numpy as np
from ..kernel.entity import Entity
from ..kernel.timeline import Timeline
from ..topology.node import Node
from ..protocol import Protocol
from .photon import Photon
from .transducer import Transducer
from sequence.constants import KET1


class Transmon(Entity):
    """Class modeling a transmon qubit.

    The Transmon class can be configured to emit microwave photons.

    Attributes:
        name (str): the name of the transmon
        timeline (Timeline): the simulation timeline
        owner (Node): the entity that owns or aggregates the current component
        wavelengths (list): two wavelengths, one for microwave, and one for optics
        photon_counter (int): photon counter
        photongs_quantum_state (list): a list of quantum states
        efficiency (float): the efficiency of the transmon
        input_quantum_state (np.array): two qubit state for microwave and optical photon
        photon0 (Photon): microwave photon
        photon1 (Photon): optical photon
    """

    def __init__(self, owner: Node, name: str, timeline: Timeline, wavelengths: List[int], photon_counter: int, photons_quantum_state: List[tuple], efficiency: float = 1):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        assert len(wavelengths) == 2
        self.wavelengths = wavelengths
        self.photon_counter = photon_counter 
        self.photons_quantum_state = photons_quantum_state 
        self.efficiency = efficiency
        self.input_quantum_state = None
              
    def init(self):
        pass

    def add_outputs(self, outputs: List):
        """Add outputs, i.e., receivers, of the transmon
        """
        for i in outputs:
            self.add_receiver(i)

    def generation(self):
        """Set tranmson quantum state and return a photon with some specifications"""
        input_quantum_state = np.kron(self.photons_quantum_state[0], self.photons_quantum_state[1])
        self.input_quantum_state = input_quantum_state

        return Photon(name="photon", timeline=self.timeline, wavelength=self.wavelengths[0], quantum_state=self.photons_quantum_state[0])
        
    def get(self, photon: Photon) -> None:
        """Receive photon from the transducer
        
        In the Direct Conversion, called when the receiver node's transducer successfully down convert the photon to microwave
        In the Entanglement Swapping, called when the transducer at the end nodes fail to up convert the microwave into photon
        """
        self.photon_counter += 1
        print(f"Photon received by the Transmon at Rx: {photon}, Name: {photon.name}, Wavelength: {photon.wavelength}")
        print(f"Photon counter of TRANSMON {self.photon_counter}")

    def receive_photon(self, photon: Photon) -> None:
        self.photon_counter += 1


class EmittingProtocol(Protocol):
    """Protocol for emission of single microwave photon by transmon.

    Attributes:
        owner (Node): the owner of this protocol, the protocol runs on the owner
        name (str): the name of the protocol
        tl (Timeline): the simulation timeline
        transmon (Transmon): the transmon component
        transducer (Transducer): the transducer component
    """

    def __init__(self, owner: "Node", name: str, tl: Timeline, transmon: Transmon, transducer: Transducer):
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
