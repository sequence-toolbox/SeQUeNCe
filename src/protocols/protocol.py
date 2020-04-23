from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import Node
    from .message import Message


class Protocol(ABC):
    def __init__(self, own: "Node", name: str):
        self.own = own
        self.name = name

    @abstractmethod
    def received_message(self, src: str, msg: "Message"):
        '''
        receive classical message from another node
        '''
        pass


class StackProtocol(Protocol):
    def __init__(self, own: "Node", name: str):
        super().__init__(own, name)
        self.upper_protocols = []
        self.lower_protocols = []

    @abstractmethod
    def push(self, **kwargs):
        pass

    @abstractmethod
    def pop(self, **kwargs):
        pass

    def _push(self, **kwargs):
        for protocol in self.lower_protocols:
            protocol.push(**kwargs)

    def _pop(self, **kwargs):
        for protocol in self.upper_protocols:
            protocol.pop(**kwargs)
