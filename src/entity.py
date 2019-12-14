from abc import ABC, abstractmethod


class Entity(ABC):

    def __init__(self, name, timeline):
        if name is None:
            self.name = ""
        else:
            self.name = name
        self.timeline = timeline
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


