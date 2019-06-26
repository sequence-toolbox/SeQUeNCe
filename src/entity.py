from abc import ABC, abstractmethod


class Entity(ABC):

    def __init__(self, timeline, name=None):
        if name is None:
            self.__name = ""
        else:
            self.__name = name
        self.__timeline = timeline

        # TODO: what to do if name is not specified

    @abstractmethod
    def init(self):
        pass
