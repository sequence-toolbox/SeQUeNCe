"""Definition of abstract Entity class.

This module defines the Entity class, inherited by all physical simulation elements (including hardware and photons).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

from numpy.random import default_rng
from numpy.random._generator import Generator

if TYPE_CHECKING:
    from ..components.photon import Photon
    from .timeline import Timeline


class Entity(ABC):
    """Abstract Entity class.
    Entity should use the provided pseudo random number generator (PRNG) to
    produce reproducible random numbers. As a result, simulations with the same
    seed can reproduce identical results. Function "get_generator" returns the PRNG.

    Attributes:
        name (str): name of the entity.
        timeline (Timeline): the simulation timeline for the entity.
        owner (Entity | None): another entity that owns or aggregates the current entity.
        _observers (list[Any]): a list of observers for the entity.
        _receivers (list[Entity]): a list of entities that receive photons from current component.
    """

    def __init__(self, name: str, timeline: "Timeline") -> None:
        """Constructor for entity class.

        Args:
            name (str): name of entity.
            timeline (Timeline): timeline for simulation.
        """
        self.name: str = name
        self.timeline: "Timeline" = timeline
        self.owner: Entity | None = None
        self._observers: list[Any] = []
        self._receivers: list["Entity"] = []
        timeline.add_entity(self)

    def __str__(self) -> str:
        return self.name

    @abstractmethod
    def init(self) -> None:
        """Method to initialize entity (abstract).

        Entity `init` methods are invoked for all timeline entities when the timeline is initialized.
        This method can be used to perform any necessary functions before simulation.
        """
        pass

    def add_receiver(self, receiver: "Entity") -> None:
        """Method to add a receiver (to receive photons)."""
        self._receivers.append(receiver)

    def attach(self, observer: Any) -> None:
        """Method to add an observer (to receive hardware updates)."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Any) -> None:
        """Method to remove an observer."""
        self._observers.remove(observer)

    def notify(self, info: dict[str, Any]) -> None:
        """Method to notify all attached observers of an update."""
        for observer in self._observers:
            observer.update(self, info)

    def get(self, photon: "Photon", **kwargs):
        """Method for an entity to receive a photon.

        If entity is a node, may forward to external quantum channel.
        Must be overwritten to be used, or will raise exception.

        Args:
            photon (Photon): photon received by the entity.
            **kwargs: other arguments required by a particular hardware component.
        """
        raise Exception("get method called on non-receiving class.")

    def remove_from_timeline(self) -> None:
        """Method to remove entity from attached timeline.

        This is to allow unused entities to be garbage collected.
        """
        self.timeline.remove_entity_by_name(self.name)

    def get_generator(self) -> Generator:
        """Method to get random generator of parent node.

        If entity is not attached to a node, return default generator.
        """
        if hasattr(self.owner, "get_generator"):
            return cast(Entity, self.owner).get_generator()
        else:
            return default_rng()

    def change_timeline(self, timeline: "Timeline"):
        self.remove_from_timeline()
        self.timeline = timeline
        self.timeline.add_entity(self)


class ClassicalEntity(Entity):
    """Abstract Entity class for purely classical entities.
    Entity should use the provided pseudo random number generator (PRNG) to
    produce reproducible random numbers. As a result, simulations with the same
    seed can reproduce identical results. Function "get_generator" returns the PRNG.

    Compared with Entity, ClassicalEntity does not have _observers and _receivers

    Attributes:
        name (str): name of the entity.
        timeline (Timeline): the simulation timeline for the entity.
        owner (Entity): another entity that owns or aggregates the current entity.
    """

    def __init__(self, name: str, timeline: "Timeline") -> None:
        """Constructor for entity class.

        Args:
            name (str): name of entity.
            timeline (Timeline): timeline for simulation.
        """
        self.name: str = name
        self.timeline: "Timeline" = timeline
        self.owner: ClassicalEntity | None = None  # type: ignore
        timeline.add_entity(self)

    def __str__(self) -> str:
        return self.name

    @abstractmethod
    def init(self) -> None:
        """Method to initialize entity (abstract).

        Entity `init` methods are invoked for all timeline entities when the timeline is initialized.
        This method can be used to perform any necessary functions before simulation.
        """
        pass

    def remove_from_timeline(self) -> None:
        """Method to remove entity from attached timeline.

        This is to allow unused entities to be garbage collected.
        """
        self.timeline.remove_entity_by_name(self.name)

    def get_generator(self) -> Generator:
        """Method to get random generator of parent node.

        If entity is not attached to a node, return default generator.
        """
        if hasattr(self.owner, "get_generator"):
            return cast(ClassicalEntity, self.owner).get_generator()
        else:
            return default_rng()

    def change_timeline(self, timeline: "Timeline"):
        self.remove_from_timeline()
        self.timeline = timeline
        self.timeline.add_entity(self)

    @property
    def _receivers(self):  # type: ignore
        raise AttributeError(
            'ClassicalEntity does not support _receivers attribute')

    @property
    def _observers(self):  # type: ignore
        raise AttributeError(
            'ClassicalEntity does not support _observers attribute')

    def add_receiver(self, receiver):
        raise NotImplementedError(
            'ClassicalEntity does not support add_receiver method')

    def attach(self, observer):
        raise NotImplementedError(
            'ClassicalEntity does not support attach method')

    def detach(self, observer):
        raise NotImplementedError(
            'ClassicalEntity does not support detach method')

    def notify(self, info):
        raise NotImplementedError(
            'ClassicalEntity does not support notify method')

    def get(self, photon, **kwargs):
        raise NotImplementedError(
            'ClassicalEntity does not support get method')
