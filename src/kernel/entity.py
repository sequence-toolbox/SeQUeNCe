"""Definition of abstract Entity class.

This module defines the Entity class, inherited by all physical simulation elements (including hardware and photons).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .timeline import Timeline


class Entity(ABC):
    """Abstract Entity class

    Args:
        name (str): name of the entity
        timeline (Timeline): the simulation timeline of entity
    """
    def __init__(self, name: str, timeline: "Timeline"):
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
        pass

    def attach(self, observer: Any):
        self._observers.append(observer)

    def detach(self, observer: Any):
        self._observers.remove(observer)

    def notify(self, msg: Dict[str, Any]):
        for observer in self._observers:
            observer.update(self, msg)

    def remove_from_timeline(self):
        self.timeline.entities.remove(self)
