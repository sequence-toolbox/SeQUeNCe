import math

from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.network_management.network_manager import *
from sequence.network_management.reservation import RSVPMsgType
from sequence.protocol import StackProtocol
from sequence.topology.node import QuantumRouter, BSMNode


class FakeNode(QuantumRouter):
    def __init__(self, name, timeline, memo_size=50):
        super().__init__(name, timeline, memo_size)
        memo_arr = self.get_components_by_type("MemoryArray")[0]
        self.network_manager = NewNetworkManager(self, memo_arr.name)
        self.send_log = []
        self.receive_log = []
        self.send_out = True

    def receive_message(self, src: str, msg: "Message") -> None:
        if msg.receiver == "network_manager":
            self.receive_log.append((src, msg))
            self.network_manager.received_message(src, msg)
        else:
            super().receive_message(src, msg)

    def send_message(self, dst: str, msg: "Message", priority=math.inf) -> None:
        self.send_log.append([dst, msg])
        if self.send_out:
            super().send_message(dst, msg, priority)

    def reset(self):
        self.send_log = []
        self.receive_log = []


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
    tl = Timeline()
    node = FakeNode('fake', tl)
    protocol = FakeProtocol(None, "protocol")
    manager = NetworkManager(node, [protocol])
    assert protocol.is_pop is False
    msg = NetworkManagerMessage("", "network_manager", "payload")
    manager.received_message("src", msg)
    assert protocol.is_pop is True


def test_NetworkManager_load_stack():
    tl = Timeline()
    node = FakeNode('fake', tl)
    manager = NetworkManager(node, [])
    assert len(manager.protocol_stack) == 0
    protocol = FakeProtocol(None, "protocol")
    manager.load_stack([protocol])
    assert len(manager.protocol_stack) == 1
    assert protocol.upper_protocols[0] == manager and protocol.lower_protocols[0] == manager


def test_NetworkManager_push():
    tl = Timeline()
    node = FakeNode("node", tl)
    node.send_out = False
    assert len(node.send_log) == 0
    node.network_manager.push(dst="dst", msg="msg")
    assert len(node.send_log) == 1
    assert node.send_log[0][0] == "dst" and isinstance(node.send_log[0][1], NetworkManagerMessage)


def test_NetworkManager():
    tl = Timeline(1e10)
    n1 = FakeNode("n1", tl, 50)
    n2 = FakeNode("n2", tl, 50)
    n3 = FakeNode("n3", tl, 20)
    m1 = BSMNode("m1", tl, ["n1", "n2"])
    m2 = BSMNode("m2", tl, ["n2", "n3"])
    n1.add_bsm_node(m1.name, n2.name)
    n2.add_bsm_node(m1.name, n1.name)
    n2.add_bsm_node(m2.name, n3.name)
    n3.add_bsm_node(m2.name, n2.name)

    for src in [n1, n2, n3, m1, m2]:
        for dst in [n1, n2, n3, m1, m2]:
            if src.name != dst.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst.name), tl,
                                      10, delay=1e5)
                cc.set_ends(src, dst.name)

    qc = QuantumChannel("qc_n1_m1", tl, 0, 10)
    qc.set_ends(n1, m1.name)
    qc = QuantumChannel("qc_n2_m1", tl, 0, 10)
    qc.set_ends(n2, m1.name)
    qc = QuantumChannel("qc_n2_m2", tl, 0, 10)
    qc.set_ends(n2, m2.name)
    qc = QuantumChannel("qc_n3_m2", tl, 0, 10)
    qc.set_ends(n3, m2.name)

    n1.network_manager.protocol_stack[0].add_forwarding_rule("n2", "n2")
    n1.network_manager.protocol_stack[0].add_forwarding_rule("n3", "n2")
    n2.network_manager.protocol_stack[0].add_forwarding_rule("n1", "n1")
    n2.network_manager.protocol_stack[0].add_forwarding_rule("n3", "n3")
    n3.network_manager.protocol_stack[0].add_forwarding_rule("n1", "n2")
    n3.network_manager.protocol_stack[0].add_forwarding_rule("n2", "n2")

    tl.init()

    # approved request
    n1.network_manager.request("n3", 1e12, 2e12, 20, 0.9)
    tl.run()
    assert len(n1.send_log) == len(n1.receive_log) == 1
    assert n1.send_log[0][0] == "n2" and n1.receive_log[0][0] == "n2"
    assert n1.send_log[0][1].payload.payload.msg_type == RSVPMsgType.REQUEST 
    assert n1.receive_log[0][1].payload.payload.msg_type == RSVPMsgType.APPROVE
    assert len(n2.send_log) == len(n2.receive_log) == 2
    assert n2.send_log[0][0] == "n3" and n2.receive_log[0][0] == "n1"
    assert n2.send_log[1][0] == "n1" and n2.receive_log[1][0] == "n3"
    assert len(n3.send_log) == len(n3.receive_log) == 1
    assert n3.send_log[0][0] == "n2" and n3.receive_log[0][0] == "n2"

    n1.reset()
    n2.reset()
    n3.reset()

    # rejected request
    n1.network_manager.request("n3", 3e12, 4e12, 50, 0.9)
    tl.run()
    assert len(n1.send_log) == len(n1.receive_log) == 1
    assert n1.send_log[0][0] == "n2" and n1.receive_log[0][0] == "n2"
    assert n1.send_log[0][1].payload.payload.msg_type == RSVPMsgType.REQUEST
    assert n1.receive_log[0][1].payload.payload.msg_type == RSVPMsgType.REJECT
    assert len(n2.send_log) == len(n2.receive_log) == 1
    assert n2.send_log[0][0] == "n1" and n2.receive_log[0][0] == "n1"

    n1.reset()
    n2.reset()
    n3.reset()

    n1.network_manager.request("n3", 5e12, 6e12, 25, 0.9)
    tl.run()
    assert len(n1.send_log) == len(n1.receive_log) == 1
    assert n1.send_log[0][0] == "n2" and n1.receive_log[0][0] == "n2"
    assert n1.send_log[0][1].payload.payload.msg_type == RSVPMsgType.REQUEST
    assert n1.receive_log[0][1].payload.payload.msg_type == RSVPMsgType.REJECT
    assert len(n2.send_log) == len(n2.receive_log) == 2
    assert n2.send_log[0][0] == "n3" and n2.receive_log[0][0] == "n1"
    assert n2.send_log[1][0] == "n1" and n2.receive_log[1][0] == "n3"
    assert len(n3.send_log) == len(n3.receive_log) == 1
    assert n3.send_log[0][0] == "n2" and n3.receive_log[0][0] == "n2"
