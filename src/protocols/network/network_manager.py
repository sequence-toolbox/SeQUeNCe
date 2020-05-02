from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...topology.node import QuantumRouter
    from ..protocol import StackProtocol

from ..message import Message


class NetworkManagerMessage(Message):
    def __init__(self, msg_type: str, receiver: str, payload: "Message"):
        Message.__init__(self, msg_type, receiver)
        self.payload = payload


class NetworkManager():
    def __init__(self, owner: "QuantumRouter", protocol_stack: "List[StackProtocol]"):
        self.name = "network_manager"
        self.owner = owner
        self.protocol_stack = protocol_stack
        self.load_stack(protocol_stack)

    def load_stack(self, stack: "List[StackProtocol]"):
        self.protocol_stack = stack
        if len(self.protocol_stack) > 0:
            self.protocol_stack[0].lower_protocols.append(self)
            self.protocol_stack[-1].upper_protocols.append(self)

    def push(self, **kwargs):
        message = NetworkManagerMessage("", "network_manager", kwargs["msg"])
        self.owner.send_message(kwargs["dst"], message)

    def pop(self, **kwargs):
        pass

    def received_message(self, src: str, msg: "NetworkManagerMessage"):
        self.protocol_stack[0].pop(src=src, msg=msg.payload)
