"""Definition of abstract Entity class.

This module defines the Entity class, inherited by all physical simulation elements (including hardware and photons).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
        timeline.entities.append(self)

        # connected entities
        self.parents = []
        self.children = []

        # connected protocols
        self.upper_protocols = []

    @abstractmethod
    def init(self):
        pass

    def push(self, **kwargs):
        pass

    def pop(self, **kwargs):
        pass

    def _push(self, **kwargs):
        for entity in self.children:
            entity.push(**kwargs)

    def _pop(self, **kwargs):
        if len(self.upper_protocols) > 0:
            for protocol in self.upper_protocols:
                protocol.pop(**kwargs)
        else:
            for entity in self.parents:
                entity.pop(**kwargs)

    def remove_from_timeline(self):
        self.timeline.entities.remove(self)


