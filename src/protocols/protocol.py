from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import Node
    from .message import Message


class Protocol(ABC):
    def __init__(self, own: "Node"):
        self.own = own
        self.own.protocols.append(self)

    @abstractmethod
    def received_message(self, src: str, msg: "Message"):
        '''
        receive classical message from another node
        '''
        pass


