import math
from abc import ABC
from typing import List, Dict

from protocols import Protocol

from sequence import topology
from sequence.process import Process
from sequence.event import Event
from protocols import EntanglementGeneration, BBPSSW, EntanglementSwapping, EndProtocol, Protocol


class Message(ABC):
    def __init__(self, msg_type):
        self.msg_type = msg_type
        self.owner_type = None
        self.payload = None


class RoutingMessage(Message):
    def __init__(self, msg_type, payload):
        Message.__init__(self, msg_type)
        self.owner_type = type(RoutingProtocol(None, None))
        self.payload = payload


class ResourceReservationMessage(Message):
    def __init__(self, msg_type: str):
        Message.__init__(self, msg_type)
        self.owner_type = type(ResourceReservationProtocol(None))
        self.responder = None
        self.initiator = None
        self.start_time = None
        self.end_time = None
        if self.msg_type == "REQUEST":
            self.fidelity = None
            self.memory_size = None
            self.qcaps = []
        elif self.msg_type == "REJECT":
            pass
        elif self.msg_type == "RESPONSE":
            self.rulesets = None
        else:
            raise Exception("Unknown type of message")

    def __str__(self):
        common = "ResourceReservationProtocol: \n\ttype=%s, \n\tinitiator=%s, \n\tresponder=%s, \n\tstart time=%d, \n\tend time=%d" % (self.msg_type, self.initiator, self.responder, self.start_time, self.end_time)
        if self.msg_type == "REQUEST":
            return common + ("\n\tfidelity=%.2f, \n\tmemory_size=%d, \n\tqcaps length=%s" % (self.fidelity, self.memory_size, len(self.qcaps)))
        elif self.msg_type == "REJECT":
            return common
        elif self.msg_type == "RESPONSE":
            return common + ("\n\trulesets=%s" % self.rulesets)

