from abc import ABC, abstractmethod
from typing import List
from numpy.random import random
from math import ceil, sqrt

from sequence import topology
from sequence import timeline
from sequence import encoding
from sequence.topology import Node
from sequence.process import Process
from sequence.event import Event


class Protocol(ABC):
    def __init__(self, own: Node):
        self.upper_protocols = []
        self.lower_protocols = []
        self.own = own
        self.own.protocols.append(self)

    @abstractmethod
    def pop(self, **kwargs):
        '''
        information generated in current protocol is popped to
        all its parents protocols
        '''
        pass

    @abstractmethod
    def push(self, **kwargs):
        '''
        information generated in current protocol is pushed to
        all its child protocols
        '''
        pass

    def _push(self, **kwargs):
        for child in self.lower_protocols:
            child.push(**kwargs)

    def _pop(self, **kwargs):
        for parent in self.upper_protocols:
            parent.pop(**kwargs)
        return

    @abstractmethod
    def received_message(self, src: str, msg: List[str]):
        '''
        receive classical message from another node
        '''
        pass

