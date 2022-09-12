"""Model for simulation of an optical switch.

This module defines the Switch class for directing the flow of photons.
The switch is usually created as part of a time bin QSDetector object, and will only accept time bin photons.
A more general switch class is in development.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .photon import Photon
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process


class Switch(Entity):
    """Class for a simple optical switch.

    Attributes:
        name (str): label for switch instance.
        timeline (Timeline): timeline for simulation.
        start_time (int): simulation start time (in ps) for transmission.
        frequency (float): frequency with which to switch destinations.
        basis_list (List[int]): 0/1 list denoting which receiver to rout photons to each period.
    """

    def __init__(self, name: str, timeline: "Timeline"):
        """Constructor for the switch class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
        """

        Entity.__init__(self, name, timeline)
        self.start_time = 0
        self.frequency = 0
        self.basis_list = []

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        pass

    def set_basis_list(self, basis_list: "List[int]", start_time: int, frequency: float) -> None:
        self.basis_list = basis_list
        self.start_time = start_time
        self.frequency = frequency

    def get(self, photon, **kwargs) -> None:
        """Method to receive photon for transmission

        Args:
            photon (Photon): photon to transmit.

        Side Effects:
            May call `get` method of attached receivers.
        """

        assert photon.encoding_type["name"] == "time_bin"

        index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
        if index < 0 or index >= len(self.basis_list):
            return

        receiver = self._receivers[self.basis_list[index]]

        # check if receiver is detector; schedule in late/early time bin
        if self.basis_list[index] == 0:
            if Photon.measure(photon.encoding_type["bases"][0], photon, self.get_generator()):
                time = self.timeline.now() + photon.encoding_type["bin_separation"]
                process = Process(receiver, "get", [photon])
                event = Event(time, process)
                self.timeline.schedule(event)
            else:
                time = self.timeline.now()
                process = Process(receiver, "get", [photon])
                event = Event(time, process)
                self.timeline.schedule(event)
        else:
            time = self.timeline.now()
            process = Process(receiver, "get", [photon])
            event = Event(time, process)
            self.timeline.schedule(event)
