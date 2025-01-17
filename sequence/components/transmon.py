"""Model for a transmon.

See https://arxiv.org/abs/2411.11377, Simulation of Quantum Transduction Strategies for Quantum Networks
"""

from typing import List
import numpy as np
from ..kernel.entity import Entity
from ..kernel.timeline import Timeline
from ..topology.node import Node
from .photon import Photon


class Transmon(Entity):
    """Class modeling a transmon qubit.

    The Transmon class can be configured to emit microwave photons.

    Attributes:
        name (str): the name of the transmon
        timeline (Timeline): the simulation timeline
        owner (Node): the entity that owns or aggregates the current component
        wavelengths (list): two wavelengths, one for microwave, and one for optics
        photon_counter (int): photon counter
        photons_quantum_state (list): a list of quantum states
        efficiency (float): the efficiency of the transmon
        input_quantum_state (np.array): two qubit state for microwave and optical photon
        new_photon0 (Photon): microwave photon
        new_photon1 (Photon): optical photon
    """

    def __init__(self, owner: Node, name: str, timeline: Timeline, wavelengths: List[int], photon_counter: int,
                 photons_quantum_state: List[tuple], efficiency: float = 1):
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
        self.new_photon0 = None
        self.new_photon1 = None        

    def init(self):
        pass

    def add_outputs(self, outputs: List):
        """Add outputs, i.e., receivers, of the transmon
        """
        for i in outputs:
            self.add_receiver(i)

    def get(self) -> None:
        """Receives a photon"""
        new_photon0 = Photon(name=self.name, timeline=self.timeline,
                             wavelength=self.wavelengths[0], quantum_state=self.photons_quantum_state[0])  # microwave
        new_photon1 = Photon(name=self.name, timeline=self.timeline,
                             wavelength=self.wavelengths[1], quantum_state=self.photons_quantum_state[1])  # optical

        input_quantum_state = np.kron(self.photons_quantum_state[0], self.photons_quantum_state[1])
        self.input_quantum_state = input_quantum_state 
        self.new_photon0 = new_photon0
        self.new_photon1 = new_photon1

    def receive_photon_from_transducer(self, photon: Photon) -> None:
        """Receive photon from the transducer
        
        In the Direct Conversion, called when the receiver node's transducer successfully down convert the photon to microwave
        In the Entanglement Swapping, called when the transducer at the end nodes fail to up convert the microwave into photon
        """
        self.photon_counter += 1

    def receive_photon(self, photon: Photon) -> None:
        self.photon_counter += 1
