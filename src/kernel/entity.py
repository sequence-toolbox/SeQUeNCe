"""Definition of abstract Entity class.

This module defines the Entity class, inherited by all physical simulation elements (including hardware and photons).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .timeline import Timeline


class Entity(ABC):
    """Abstract Entity class.

    Attributes:
        name (str): name of the entity.
        timeline (Timeline): the simulation timeline for the entity.
        owner (Entity): another entity that owns or aggregates the current entity.
        parents (List[Entity]): upper-level entities that receive `pop` notifications.
        children (List[Entity]): lower-level entities that receive `push` notifications.
        upper_protocols (List[Protocol]): connected protocols.
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
        timeline.entities.append(self)

        # connected entities
        self.parents = []
        self.children = []

        # connected protocols
        self.upper_protocols = []

    @abstractmethod
    def init(self):
        """Method to initialize entity (abstract).

        Entity `init` methods are invoked for all timeline entities when the timeline is initialized.
        This method can be used to perform any necessary functions before simulation.
        """

        pass

    def push(self, **kwargs):
        """Method to receive information from upper entities."""

        pass

    def pop(self, **kwargs):
        """Method to receive information from lower entities."""

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
        """Method to remove entity from attached timeline.

        This is to allow unused entities to be garbage collected.
        """

        self.timeline.entities.remove(self)


