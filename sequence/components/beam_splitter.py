"""Models for simulation of a polarization beam splitter.

This module defines the class BeamSplitter, which is used for simulating polarization beam splitters. 
The beam splitter receives photons with polarization encoding and forwards photons to one of two 
attached receivers (which can be any entity).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..topology.node import Node

from numpy import trace

from .photon import Photon
from ..kernel.quantum_utils import povm_0
from ..utils.encoding import polarization
from ..kernel.entity import Entity
import random



class BeamSplitter(Entity):
    """Class modeling a polarization beamsplitter.

    Simulates operation of a polarization beam splitter (PBS).
    The BeamSplitter class can be configured to measure polarization in different bases at different times.
    
    Attributes:
        name (str): label for beamsplitter instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float): probability of transmitting a received photon.
        start_time (int): start time (in ps) of photon interaction.
        frequency (float): frequency with which to switch measurement bases.
        basis_list (list[int]): 0/1 indices of measurement bases over time.
    """

    def __init__(self, name: str, timeline: "Timeline", fidelity=1):
        """Constructor for the beamsplitter class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): probability of transmitting a received photon (default 1).
        """

        Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name
        self.fidelity = fidelity
        # for BB84
        self.start_time = 0
        self.frequency = 0
        self.basis_list = []

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        assert len(self._receivers) == 2, "BeamSplitter should only be attached to 2 outputs."

    def get(self, photon, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to measure (must have polarization encoding)

        Side Effects:
            May call get method of one receiver.
        """

        assert photon.encoding_type["name"] == "polarization", "Beamsplitter should only be used with polarization."

        if self.get_generator().random() < self.fidelity:
            index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)

            if 0 > index or index >= len(self.basis_list):
                return

            res = Photon.measure(polarization["bases"][self.basis_list[index]],
                                 photon, self.get_generator())
            self._receivers[res].get(photon)

    def set_basis_list(self, basis_list: list[int], start_time: int, frequency: float) -> None:
        """Sets the basis_list, start_time, and frequency attributes."""

        self.basis_list = basis_list
        self.start_time = start_time
        self.frequency = frequency


class FockBeamSplitter(Entity):
    """WIP"""

    def __init__(self, name, timeline, fidelity=1):
        super().__init__(name, timeline)
        self.fidelity = fidelity
        self.most_recent_time = -1

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        assert len(self._receivers) == 2, "BeamSplitter should only be attached to 2 outputs."

    def get(self, photon, **kwargs) -> None:
        assert photon.encoding_type["name"] == "absorptive"

        if not photon.is_null:
            state = self.timeline.quantum_manager.get(photon.quantum_state)

            if len(state.keys) == 2:  # entangled; calculate probability of measurement
                prob_0 = trace(state.state @ povm_0).real
                if prob_0 > 1:
                    prob_0 = 1
                elif prob_0 < 0:
                    prob_0 = 0

            else:  # unentangled; send to a random output
                if self.timeline.now() == self.most_recent_time:  # if already measured right now, return (HOM effect)
                    return
                prob_0 = 0.5

            detector_num = self.get_generator().choice([0, 1], p=[prob_0, 1-prob_0])
            self.most_recent_time = self.timeline.now()
            self._receivers[detector_num].get()


class FockBeamSplitter2(Entity):
    """Class modeling a Fock beam splitter. The '2' for avoiding naming conflicts.

    A Fock beam splitter can send a single photon randomly in one of its ports. 
    See https://arxiv.org/abs/2411.11377, Simulation of Quantum Transduction Strategies for Quantum Networks

    Attributes:
        name (str): the name
        owner (Node): the owner
        timeline (Timeline): the timeline
        efficiency (float): the efficiency of the beamsplitter
        photon_counter (int): counter for counting photons
        src_list (str): a list of photon source names
    """
    def __init__(self, name: str, owner: "Node", timeline: "Timeline", efficiency: float, photon_counter: int, src_list: list[str]):

        Entity.__init__(self, name, timeline)
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = photon_counter
        self.src_list = src_list
        self.swapping_protocol = None
        self.update_counter = 0


    def init(self):
        assert len(self._receivers) == 2


    def get(self, source: str, photon: Photon) -> None:
        """Receive photon from two end nodes"""

        self.photon_counter += 1
            
        print(f"Photon counter BEAM SPLITTER: {self.photon_counter} at time {self.timeline.now()}")

        selected_receiver = random.choice(self._receivers)

        if self.photon_counter == 1:
            
            selected_receiver.get(photon)
            selected_receiver.get_2(photon) 

        elif self.photon_counter == 2:
            
            self._receivers[0].photon_counter = 0
            self._receivers[1].photon_counter = 0
            self._receivers[0].photon_counter2 = 0
            self._receivers[1].photon_counter2 = 0
            selected_receiver.getx2(photon)
            selected_receiver.get_2x2(photon)


    def add_outputs(self, outputs: list):
        """Add outputs, i.e., receivers
        
        Args:
            outputs (list): a list of entities, i.e., detectors
        """
        for i in outputs:
            self.add_receiver(i)
