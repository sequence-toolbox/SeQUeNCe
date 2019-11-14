from abc import ABC, abstractmethod

class Protocol(ABC):

    def __init__(self, parent_protocols=[], child_protocols=[]):
        self.parent_protocols = parent_protocols
        self.child_protocols = child_protocols

    @abstractmethod
    def pop(self):
        '''
        information generated in current protocol is poped to all its parents protocols
        '''
        pass

    @abstractmethod
    def push(self):
        '''
        information generated in current protocol is pushed to all its child protocols
        '''
        pass

