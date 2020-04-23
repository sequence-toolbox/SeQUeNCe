from ..protocol import Protocol


class EntanglementProtocol(Protocol):
    def __init__(self, own: "Node", name: str):
        Protocol.__init__(self, own, name)

    @staticmethod
    def set_others(self, other: "EntanglementProtocol") -> None:
        pass

    @staticmethod
    def start(self) -> None:
        pass
