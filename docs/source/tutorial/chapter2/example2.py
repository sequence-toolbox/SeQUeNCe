from enum import Enum, auto

import sequence as sq


class MsgType(Enum):
    PING = auto()
    PONG = auto()


class PingProtocol(sq.Protocol):
    def __init__(self, owner: sq.Node, name: str, other_name: str, other_node: str):
        super().__init__(owner, name)
        owner.protocols.append(self)
        self.other_name = other_name
        self.other_node = other_node

    def init(self):
        pass

    def start(self):
        new_msg = sq.Message(MsgType.PING, self.other_name)
        self.owner.send_message(self.other_node, new_msg)

    def received_message(self, src: str, message: sq.Message):
        assert message.msg_type == MsgType.PONG
        print("node {} received pong message at time {}".format(self.owner.name, self.owner.timeline.now()))


class PongProtocol(sq.Protocol):
    def __init__(self, owner: sq.Node, name: str, other_name: str, other_node: str):
        super().__init__(owner, name)
        owner.protocols.append(self)
        self.other_name = other_name
        self.other_node = other_node
    
    def init(self):
        pass

    def received_message(self, src: str, message: sq.Message):
        assert message.msg_type == MsgType.PING
        print(f"node {self.owner.name} received ping message at time {self.owner.timeline.now()}")
        new_msg = sq.Message(MsgType.PONG, self.other_name)
        self.owner.send_message(self.other_node, new_msg)


if __name__ == "__main__":
    tl = sq.Timeline(1e12)
    tl.show_progress = False

    node1 = sq.Node("node1", tl)
    node2 = sq.Node("node2", tl)
    node1.set_seed(0)
    node2.set_seed(1)

    cc0 = sq.ClassicalChannel("cc0", tl, 1e3, 1e9)
    cc1 = sq.ClassicalChannel("cc1", tl, 1e3, 1e9)
    cc0.set_ends(node1, node2.name)
    cc1.set_ends(node2, node1.name)

    pingp = PingProtocol(node1, "pingp", "pongp", "node2")
    pongp = PongProtocol(node2, "pongp", "pingp", "node1")

    process = sq.Process(pingp, "start", [])
    event = sq.Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
