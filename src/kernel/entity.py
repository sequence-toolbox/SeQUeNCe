"""Definition of abstract Entity class.

This module defines the Entity class, inherited by all physical simulation elements (including hardware and photons).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .timeline import Timeline


class Entity(ABC):
    """Abstract Entity class.

    Attributes:
        name (str): name of the entity.
        timeline (Timeline): the simulation timeline for the entity.
        owner (Entity): another entity that owns or aggregates the current entity.
        _observer (List): a list of observers for the entity.
    """

    def __init__(self, name: str, timeline: "Timeline"):
        """Constructor for entity class.

        Args:
            name (str): name of entity.
            timeline (Timeline): timeline for simulation.
        """

        if name is None:
            self.name = ""
        else:
            self.name = name
        self.timeline = timeline
        self.owner = None
        self._observers = []
        timeline.entities.append(self)

    @abstractmethod
    def init(self):
        """Method to initialize entity (abstract).

        Entity `init` methods are invoked for all timeline entities when the timeline is initialized.
        This method can be used to perform any necessary functions before simulation.
        """

        pass

    def attach(self, observer: Any):
        """Method to add an ovserver (to receive hardware updates)."""

        if not observer in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Any):
        """Method to remove an observer."""

        self._observers.remove(observer)

    def notify(self, info: Dict[str, Any]):
        """Method to notify all attached observers of an update."""

        for observer in self._observers:
            observer.update(self, info)

    def remove_from_timeline(self):
        """Method to remove entity from attached timeline.

        This is to allow unused entities to be garbage collected.
        """

        self.timeline.entities.remove(self)
