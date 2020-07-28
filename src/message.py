from enum import Enum
from abc import ABC


class Message(ABC):
    def __init__(self, msg_type: Enum, receiver: str):
        self.msg_type = msg_type
        self.receiver = receiver
        self.payload = None


