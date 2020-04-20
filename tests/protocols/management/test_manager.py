from sequence.components.memory import *
from sequence.protocols.management.manager import ResourceManagerMessage
from sequence.protocols.management.rule_manager import *
from sequence.topology.node import *


class FakeNode(Node):
    def __init__(self, name, tl):
        Node.__init__(self, name, tl)
        self.memory_array = MemoryArray(name + ".MemoryArray", tl)
        self.resource_manager = ResourceManager(self)
        self.send_log = []

    def send_message(self, dst: str, msg: "Message", priority=math.inf) -> None:
        self.send_log.append((dst, msg))


def test_load():
    def fake_condition(memo_info, manager):
        if memo_info.state == "RAW":
            return [memo_info.memory]
        else:
            return []

    def fake_action(memories):
        return "protocol", None, None

    tl = Timeline()
    node = FakeNode("node", tl)
    assert len(node.resource_manager.rule_manager) == 0
    rule = Rule(1, fake_action, fake_condition)
    for memo_info in node.resource_manager.memory_manager:
        assert memo_info.state == "RAW"
    node.resource_manager.load(rule)
    assert len(node.resource_manager.rule_manager) == 1
    for memo_info in node.resource_manager.memory_manager:
        assert memo_info.state == "OCCUPIED"
    assert len(node.resource_manager.waiting_protocols) == len(node.memory_array)
    assert len(node.resource_manager.pending_protocols) == 0
    assert len(rule.protocols) == len(node.memory_array)


def test_update():
    def fake_condition(memo_info, manager):
        if memo_info.state == "ENTANGLED" and memo_info.fidelity > 0.8:
            return [memo_info.memory]
        else:
            return []

    def fake_action(memories):
        return "protocol", None, None

    tl = Timeline()
    node = FakeNode("node", tl)
    assert len(node.resource_manager.rule_manager) == 0
    rule = Rule(1, fake_action, fake_condition)
    node.resource_manager.load(rule)
    assert len(node.resource_manager.rule_manager) == 1
    for memo_info in node.resource_manager.memory_manager:
        assert memo_info.state == "RAW"

    protocol = "protocol1"
    node.protocols.append(protocol)
    node.memory_array[0].fidelity = 0.5
    node.resource_manager.update(protocol, node.memory_array[0], "ENTANGLED")
    assert len(node.protocols) == len(rule.protocols) == 0
    assert node.resource_manager.memory_manager[0].state == "ENTANGLED"

    protocol = "protocol2"
    node.protocols.append(protocol)
    node.memory_array[1].fidelity = 0.9
    node.resource_manager.update(protocol, node.memory_array[1], "ENTANGLED")
    assert len(node.resource_manager.waiting_protocols) == len(rule.protocols) == 1
    assert node.resource_manager.memory_manager[1].state == "OCCUPIED"


def test_send_request():
    tl = Timeline()
    node = FakeNode("node", tl)
    resource_manager = node.resource_manager
    assert len(node.send_log) == 0
    resource_manager.send_request("protocol_no_send", None, None)
    assert len(node.send_log) == 0
    assert "protocol_no_send" in resource_manager.waiting_protocols and len(resource_manager.pending_protocols) == 0
    node.resource_manager.send_request("protocol_send", "dst_id", "req_condition_func")
    assert len(node.send_log) == 1
    assert "protocol_send" in resource_manager.pending_protocols and len(resource_manager.waiting_protocols) == 1


def test_received_message():
    def true_fun(protocol):
        return True

    def false_fun(protocol):
        return False

    class FakeProtocol():
        def __init__(self, name):
            self.name = name
            self.other_is_setted = False
            self.is_started = False
            self.is_released = False

        def set_others(self, other):
            self.other_is_setted = True

        def start(self):
            self.is_started = True

        def release(self):
            self.is_released = True

    tl = Timeline()
    node = FakeNode("node", tl)
    resource_manager = node.resource_manager

    # test receive REQUEST message
    protocol1 = FakeProtocol("waiting_protocol")
    resource_manager.waiting_protocols.append(protocol1)
    req_msg = ResourceManagerMessage("REQUEST", "resource_manager", protocol="ini_protocol", req_condition_fun=true_fun)
    resource_manager.received_message("sender", req_msg)
    assert protocol1 in node.protocols
    assert protocol1 not in resource_manager.waiting_protocols
    assert protocol1.other_is_setted and protocol1.is_started
    assert node.send_log[-1][0] == "sender"
    assert isinstance(node.send_log[-1][1], ResourceManagerMessage)
    assert node.send_log[-1][1].msg_type == "RESPONSE" and node.send_log[-1][1].is_approved

    protocol1 = FakeProtocol("waiting_protocol")
    resource_manager.waiting_protocols.append(protocol1)
    req_msg = ResourceManagerMessage("REQUEST", "resource_manager", protocol="ini_protocol",
                                     req_condition_fun=false_fun)
    resource_manager.received_message("sender", req_msg)
    assert protocol1 not in node.protocols
    assert protocol1 in resource_manager.waiting_protocols
    assert not protocol1.other_is_setted and not protocol1.is_started
    assert node.send_log[-1][0] == "sender"
    assert isinstance(node.send_log[-1][1], ResourceManagerMessage)
    assert node.send_log[-1][1].msg_type == "RESPONSE" and not node.send_log[-1][1].is_approved

    # test receive RESPONSE message
    protocol2 = FakeProtocol("pending_protocol")
    resource_manager.pending_protocols.append(protocol2)
    resp_msg = ResourceManagerMessage("RESPONSE", "resource_manager", protocol=protocol2, is_approved=False,
                                      paired_protocol="paired_protocol")
    resource_manager.received_message("sender", resp_msg)
    assert protocol2 not in node.protocols
    assert protocol2 not in resource_manager.pending_protocols
    assert not protocol2.other_is_setted and not protocol2.is_started and protocol2.is_released

    protocol2 = FakeProtocol("pending_protocol")
    resource_manager.pending_protocols.append(protocol2)
    resp_msg = ResourceManagerMessage("RESPONSE", "resource_manager", protocol=protocol2, is_approved=True,
                                      paired_protocol="paired_protocol")
    resource_manager.received_message("sender", resp_msg)
    assert protocol2 in node.protocols
    assert protocol2 not in resource_manager.pending_protocols
    assert protocol2.other_is_setted and protocol2.is_started and not protocol2.is_released
