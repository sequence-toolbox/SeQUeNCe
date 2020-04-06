from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from numpy.random import random

from ..message import Message
from ..protocol import Protocol


class BBPSSWMessage(Message):
    def __init__(self, msg_type: str, receiver: str, **kwargs):
        Message.__init__(self, msg_type, receiver)
        if self.msg_type == "PURIFICATION_RES":
            pass
        else:
            raise Exception("BBPSSW protocol create unkown type of message: %s" % str(msg_type))


class BBPSSW(Protocol):
    def __init__(self, own: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory"):
        assert kept_memo != meas_memo
        Protocol.__init__(self, own, name)
        self.kept_memo = kept_memo
        self.meas_memo = meas_memo
        self.another = None
        self.is_success = None

    def set_another(self, another: "BBPSSW") -> None:
        self.another = another

    def start(self) -> None:
        assert self.another is not None, "another protocol is not setted; please use set_another function to set it."
        assert (self.kept_memo.entangled_memory["node_id"] ==
                self.meas_memo.entangled_memory["node_id"] ==
                self.another.own.name)
        assert self.kept_memo.fidelity == self.meas_memo.fidelity > 0.5

        if self.is_success is None:
            if random() > self.success_probability(self.kept_memo.fidelity):
                self.is_success = self.another.is_success = True
            else:
                self.is_success = self.another.is_success = False

        if self.is_success:
            self.kept_memo.fidelity = self.improved_fidelity(self.kept_memo.fidelity)
            dst = self.another.own.name
            message = BBPSSWMessage("PURIFICATION_RES", self.another.name)
            self.own.send_message(dst, message)
        else:
            self.kept_memo.fidelity = 0
            self.kept_memo.entangled_memory["node_id"] = None
            self.kept_memo.entangled_memory["memo_id"] = None
            dst = self.another.own.name
            message = BBPSSWMessage("PURIFICATION_RES", self.another.name)
            self.own.send_message(dst, message)

        self.meas_memo.fidelity = 0
        self.meas_memo.entangled_memory["node_id"] = None
        self.meas_memo.entangled_memory["memo_id"] = None
        self.update_resource_manager(self.meas_memo, "EMPTY")

    def update_resource_manager(self, memory: "Memory", state: str) -> None:
        self.own.resource_manager.update(memory, state)

    def received_message(self, src: str, msg: List[str]) -> None:
        assert src == self.another.own.name
        if self.is_success is True:
            self.update_resource_manager(self.kept_memo, state="ENTANGLE")
        else:
            self.update_resource_manager(self.kept_memo, state="EMPTY")

    @staticmethod
    def success_probability(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) page 14
        '''
        return F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2

    @staticmethod
    def improved_fidelity(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) formula (18) page 14
        '''
        return (F ** 2 + ((1 - F) / 3) ** 2) / (F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2)

    def push(self, **kwargs) -> None:
        pass

    def pop(self, **kwargs) -> None:
        pass
