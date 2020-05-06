from typing import Dict

if TYPE_CHECKING:
    from ...topology.node import Node

from ..message import Message
from ..protocol import StackProtocol


class RoutingMessage(Message):
    def __init__(self, msg_type, payload):
        Message.__init__(self, msg_type)
        self.owner_type = type(RoutingProtocol(None, None))
        self.payload = payload


class RoutingProtocol(StackProtocol):
    def __init__(self, own: "Node", forwarding_table: Dict):
        '''
        forwarding_table: {name of destination node: name of next node}
        '''
        if own is None:
            return
        Protocol.__init__(self, own)
        self.forwarding_table = forwarding_table

    def add_forwarding_rule(self, dst: str, next_node: str):
        assert dst not in self.forwarding_table
        self.forwarding_table[dst] = next_node

    def push(self, **kwargs):
        dst = kwargs["dst"]
        assert dst in self.forwarding_table
        kwargs["dst"] = self.forwarding_table[dst]
        self._push(**kwargs)

    def pop(self, **kwargs):
        self._pop(**kwargs)

    def received_message(self, src: str, msg: RoutingMessage):
        self._pop(msg=msg.payload, src=src)

    def init(self):
        pass


