from abc import ABC


class Message(ABC):
    def __init__(self, msg_type: str, receiver: str):
        self.receiver = receiver
        self.msg_type = msg_type
        self.payload = None
