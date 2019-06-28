from abc import ABC, abstractmethod


class Entity(ABC):

    def __init__(self, name, timeline):
        if name is None:
            self.__name = ""
        else:
            self.__name = name
        self.__timeline = timeline

    @abstractmethod
    def init(self):
        pass
