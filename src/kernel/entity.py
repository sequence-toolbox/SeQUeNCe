from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .timeline import Timeline


class Entity(ABC):

    def __init__(self, name: str, timeline: "Timeline"):
        if name is None:
            self.name = ""
        else:
            self.name = name
        self.timeline = timeline
        self.owner = None
        timeline.entities.append(self)

        self.parents = []
        self.children = []

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
        for entity in self.parents:
            entity.pop(**kwargs)

    def remove_from_timeline(self):
        self.timeline.entities.remove(self)


