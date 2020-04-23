from ..protocol import Protocol


class EntanglementProtocol(Protocol):
    def __init__(self, own: "Node", name: str):
        Protocol.__init__(self, own, name)

    @staticmethod
    def set_others(self, other):
        pass

    @staticmethod
    def start(self):
        pass
