import math
from abc import ABC
from typing import List, Dict

from protocols import Protocol

from sequence import topology
from sequence.process import Process
from sequence.event import Event
from protocols import EntanglementGeneration, BBPSSW, EntanglementSwapping, EndProtocol, Protocol


class RoutingProtocol(Protocol):
    def __init__(self, own, forwarding_table: Dict):
        '''
        forwarding_table: {name of destination node: name of next node}
        '''
        if own is None:
            return
        Protocol.__init__(self, own)
        self.forwarding_table = forwarding_table

    def add_forwarding_rule(self, dst, next_node):
        assert dst not in self.forwarding_table
        self.forwarding_table[dst] = next_node

    def push(self, msg: Message, dst: str):
        assert dst in self.forwarding_table

        next_node = self.forwarding_table[dst]
        msg = RoutingMessage(None, payload=msg)
        self.own.send_message(next_node, msg)

    def pop(self):
        pass

    def received_message(self, src: str, msg: RoutingMessage):
        # print(self.own.timeline.now(), ':', self.own.name, "received_message from", src, "; msg is (", msg, ")")
        self._pop(msg=msg.payload, src=src)


    def init(self):
        pass

