import math

from sequence.kernel.timeline import Timeline
from sequence.protocols.network.network_manager import NetworkManager, NetworkManagerMessage
from sequence.protocols.protocol import StackProtocol
from sequence.topology.node import QuantumRouter


class FakeNode(QuantumRouter):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.network_manager = NetworkManager(self, [])
        self.send_log = []

    def receive_message(self, src: str, msg: "Message") -> None:
        if msg.receiver == "network_manager":
            self.network_manager.received_message(src, msg)
        else:
            super().receive_message(src, msg)

    def send_message(self, dst: str, msg: "Message", priority=math.inf) -> None:
        self.send_log.append([dst, msg])


class FakeProtocol(StackProtocol):
    def __init__(self, owner, name):
        super().__init__(owner, name)
        self.is_pop = False
        self.is_push = False

    def pop(self, **kwargs):
        self.is_pop = True

    def push(self, **kwargs):
        self.is_push = True


def test_NetworkManager_received_message():
    protocol = FakeProtocol(None, "protocol")
    manager = NetworkManager(None, [protocol])
    assert protocol.is_pop is False
    msg = NetworkManagerMessage("", "network_manager", "payload")
    manager.received_message("src", msg)
    assert protocol.is_pop is True


def test_NetworkManager_load_stack():
    manager = NetworkManager(None, [])
    assert len(manager.protocol_stack) == 0
    protocol = FakeProtocol(None, "protocol")
    manager.load_stack([protocol])
    assert len(manager.protocol_stack) == 1
    assert protocol.upper_protocols[0] == manager and protocol.lower_protocols[0] == manager


def test_NetworkManager_push():
    tl = Timeline()
    node = FakeNode("node", tl)
    assert len(node.send_log) == 0
    node.network_manager.push(dst="dst", msg="msg")
    assert len(node.send_log) == 1
    assert node.send_log[0][0] == "dst" and isinstance(node.send_log[0][1], NetworkManagerMessage)
