from abc import ABC, abstractmethod


class Entity(ABC):

    def __init__(self, name, timeline):
        if name is None:
            self.name = ""
        else:
            self.name = name
        self.timeline = timeline

    @abstractmethod
    def init(self):
        pass
