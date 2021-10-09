"""Models for simulation of a polarization beam splitter.

This module defines the class BeamSplitter, which is used for simulating polarization beam splitters. 
The beam splitter receives photons with polarization encoding and forwards photons to one of two 
attached receivers (which can be any entity).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .photon import Photon
from ..utils.encoding import polarization
from ..kernel.entity import Entity


class BeamSplitter(Entity):
    """Class modeling a polarization beamsplitter.

    Simulates operation of a polarization beam splitter (PBS).
    The BeamSplitter class can be configured to measure polarization in different bases at different times.
    
    Attributes:
        name (str): label for beamsplitter instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float): probability of transmitting a received photon.
        receivers (List[Entities]): entities to receive transmitted photons.
        start_time (int): start time (in ps) of photon interaction.
        frequency (float): frequency with which to switch measurement bases.
        basis_list (List[int]): 0/1 indices of measurement bases over time.
    """

    def __init__(self, name: str, timeline: "Timeline", fidelity=1):
        """Constructor for the beamsplitter class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.

        Keyword Args:
            fidelity (float): probability of transmitting a received photon (default 1).
        """

        Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name
        self.fidelity = fidelity
        self.receivers = []
        # for BB84
        self.start_time = 0
        self.frequency = 0
        self.basis_list = []

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        pass

    def get(self, photon: "Photon") -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to measure (must have polarization encoding)

        Side Effects:
            May call get method of one receiver from the receivers attribute if start_time, frequency, and basis_list attributes are set up properly.
        """

        assert photon.encoding_type["name"] == "polarization"

        if self.get_generator().random() < self.fidelity:
            index = int((
                                    self.timeline.now() - self.start_time) * self.frequency * 1e-12)

            if 0 > index or index >= len(self.basis_list):
                return

            res = Photon.measure(polarization["bases"][self.basis_list[index]],
                                 photon, self.get_generator())
            self.receivers[res].get()

    def set_basis_list(self, basis_list: "List[int]", start_time: int, frequency: int) -> None:
        """Sets the basis_list, start_time, and frequency attributes."""

        self.basis_list = basis_list
        self.start_time = start_time
        self.frequency = frequency

    def set_receiver(self, index: int, receiver: "Entity") -> None:
        """Sets the receivers attribute at the specified index."""

        if index > len(self.receivers):
            raise Exception("index is larger than the length of receivers")
        self.receivers.insert(index, receiver)
