"""Model for a transducer.

See https://arxiv.org/abs/2411.11377, Simulation of Quantum Transduction Strategies for Quantum Networks
"""

from typing import List

from ..kernel.entity import Entity
from ..kernel.timeline import Timeline
from ..topology.node import Node
from .photon import Photon


class Transducer(Entity):
    """Class modeling a transducer.

    A transducer can operate in two modes: up-conversion and down-conversion.
    In up-conversion it can convert microwave photons to optical photons.
    In down-conversion it can convert optical photons to microwave photons.

    Attributes:
        name (str): the name of the transducer
        timeline (Timeline): the simulation timeline
        owner (Node): the entity that owns or aggregates the current component
        efficiency (float): the efficiency of the transducer
        photon_counter (int): photon counter
    """
    def __init__(self, owner: Node, name: str, timeline: Timeline, efficiency: float = 1):
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = 0
        
    def init(self):
        assert len(self._receivers) == 2

    def add_outputs(self, outputs: List):
        """Add outputs, i.e., receivers"""
        for i in outputs:
            self.add_receiver(i)
    
    def receive_photon_from_transmon(self, photon: Photon) -> None:
        """Receive a photon from the transmon"""
        # NOTE should schedule an UpConvert event in the future,
        # and pass on the argument photon to the UpConversion protocol's convert() method
        self.photon_counter += 1

    def receive_photon_from_channel(self, photon: Photon) -> None:
        self.photon_counter += 1
