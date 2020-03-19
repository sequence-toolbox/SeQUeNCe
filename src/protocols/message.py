from abc import ABC


class Message(ABC):
    def __init__(self, msg_type: str):
        self.msg_type = msg_type
        self.owner_type = None
        self.payload = None
