from abc import ABC, abstractmethod


class Entity(ABC):

    def __init__(self, timeline, name=None):
        if name is None:
            self.name = ""
        else:
            self.name = name
        self.timeline = timeline

        # TODO: what to do if name is not specified

    @abstractmethod
    def init(self):
        pass
