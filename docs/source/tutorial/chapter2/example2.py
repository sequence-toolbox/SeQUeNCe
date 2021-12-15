from enum import Enum, auto

from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.optical_channel import ClassicalChannel
from sequence.topology.node import Node
from sequence.protocol import Protocol
from sequence.message import Message


class MsgType(Enum):
    PING = auto()
    PONG = auto()


class PingProtocol(Protocol):
    def __init__(self, own: Node, name: str, other_name: str, other_node: str):
        super().__init__(own, name)
        own.protocols.append(self)
        self.other_name = other_name
        self.other_node = other_node

    def init(self):
        pass

    def start(self):
        new_msg = Message(MsgType.PING, self.other_name)
        self.own.send_message(self.other_node, new_msg)

    def received_message(self, src: str, message: Message):
        assert message.msg_type == MsgType.PONG
        print("node {} received pong message at time {}".format(self.own.name, self.own.timeline.now()))


class PongProtocol(Protocol):
    def __init__(self, own: Node, name: str, other_name: str, other_node: str):
        super().__init__(own, name)
        own.protocols.append(self)
        self.other_name = other_name
        self.other_node = other_node
    
    def init(self):
        pass

    def received_message(self, src: str, message: Message):
        assert message.msg_type == MsgType.PING
        print("node {} received ping message at time {}".format(self.own.name, self.own.timeline.now()))
        new_msg = Message(MsgType.PONG, self.other_name)
        self.own.send_message(self.other_node, new_msg)


if __name__ == "__main__":
    tl = Timeline(1e12)
    tl.show_progress = False

    node1 = Node("node1", tl)
    node2 = Node("node2", tl)
    node1.set_seed(0)
    node2.set_seed(1)

    cc0 = ClassicalChannel("cc0", tl, 1e3, 1e9)
    cc1 = ClassicalChannel("cc1", tl, 1e3, 1e9)
    cc0.set_ends(node1, node2.name)
    cc1.set_ends(node2, node1.name)

    pingp = PingProtocol(node1, "pingp", "pongp", "node2")
    pongp = PongProtocol(node2, "pongp", "pingp", "node1")

    process = Process(pingp, "start", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
