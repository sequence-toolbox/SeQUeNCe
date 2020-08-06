"""Code for BBPSSW entanglement purification.

This module defines code to support the BBPSSW protocol for entanglement purification.
Success results are pre-determined based on network parameters.
Also defined is the message type used by the BBPSSW code.
"""

from enum import Enum, auto
from typing import List, TYPE_CHECKING
from functools import lru_cache

from numpy.random import random

if TYPE_CHECKING:
    from ..components.memory import Memory
    from ..topology.node import Node

from ..message import Message
from .entanglement_protocol import EntanglementProtocol


class BBPSSWMsgType(Enum):
    """Defines possible message types for entanglement purification"""

    PURIFICATION_RES = auto()


class BBPSSWMessage(Message):
    """Message used by entanglement purification protocols.

    This message contains all information passed between purification protocol instances.

    Attributes:
        msg_type (BBPSSWMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
    """

    def __init__(self, msg_type: BBPSSWMsgType, receiver: str, **kwargs):
        Message.__init__(self, msg_type, receiver)
        if self.msg_type is BBPSSWMsgType.PURIFICATION_RES:
            pass
        else:
            raise Exception("BBPSSW protocol create unknown type of message: %s" % str(msg_type))


class BBPSSW(EntanglementProtocol):
    """Purification protocol instance.

    This class provides an implementation of the BBPSSW purification protocol.
    It should be instantiated on a quantum router node.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        kept_memo: memory to be purified by the protocol (should already be entangled).
        meas_memo: memory to measure and discart (should already be entangled).
    """

    def __init__(self, own: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory"):
        assert kept_memo != meas_memo
        EntanglementProtocol.__init__(self, own, name)
        self.memories = [kept_memo, meas_memo]
        self.kept_memo = kept_memo
        self.meas_memo = meas_memo
        self.is_primary = meas_memo is not None
        self.t0 = self.kept_memo.timeline.now()
        self.another = None
        self.is_success = None
        if self.meas_memo is None:
            self.memories.pop()

    def is_ready(self) -> bool:
        return self.another is not None

    def set_others(self, another: "BBPSSW") -> None:
        self.another = another

    def start(self) -> None:
        assert self.another is not None, "another protocol is not setted; please use set_another function to set it."
        assert (self.kept_memo.entangled_memory["node_id"] ==
                self.meas_memo.entangled_memory["node_id"])
        assert self.kept_memo.fidelity == self.meas_memo.fidelity > 0.5

        if self.is_success is None:
            if random() < self.success_probability(self.kept_memo.fidelity):
                self.is_success = self.another.is_success = True
            else:
                self.is_success = self.another.is_success = False

        dst = self.kept_memo.entangled_memory["node_id"]
        if self.is_success:
            self.kept_memo.fidelity = self.improved_fidelity(self.kept_memo.fidelity)

        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, self.another.name)
        self.own.send_message(dst, message)

    def update_resource_manager(self, memory: "Memory", state: str) -> None:
        if state == 'RAW':
            memory.fidelity = 0
            memory.entangled_memory['node_id'] = None
            memory.entangled_memory['memo_id'] = None

        self.own.resource_manager.update(self, memory, state)

    def received_message(self, src: str, msg: List[str]) -> None:
        assert src == self.another.own.name
        self.update_resource_manager(self.meas_memo, "RAW")
        if self.is_success is True:
            self.update_resource_manager(self.kept_memo, state="ENTANGLED")
        else:
            self.update_resource_manager(self.kept_memo, state="RAW")

    def memory_expire(self, memory: "Memory") -> None:
        assert memory in self.memories
        if self.meas_memo is None:
            self.update_resource_manager(memory, "RAW")
        else:
            delay = self.own.cchannels[self.kept_memo.entangled_memory["node_id"]].delay
            if self.is_primary:
                if self.own.timeline.now() < self.t0 + delay:
                    self.update_resource_manager(memory, "RAW")
                    for memory1 in self.memories:
                        if memory1 != memory:
                            self.update_resource_manager(memory1, "ENTANGLED")
                elif self.own.timeline.now() < self.t0 + 2 * delay:
                    for memory1 in self.memories:
                        self.update_resource_manager(memory1, "RAW")
                else:
                    raise Exception("invalid call time, t0:%d, delay:%d" % (self.t0, delay))
            else:
                if self.own.timeline.now() < self.t0 + delay:
                    for memory1 in self.memories:
                        self.update_resource_manager(memory1, "RAW")
                elif self.own.timeline.now() < self.t0 + 2 * delay:
                    if memory == self.kept_memo:
                        for memory1 in self.memories:
                            self.update_resource_manager(memory1, "RAW")

    def release(self) -> None:
        pass

    @staticmethod
    @lru_cache(maxsize=128)
    def success_probability(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) page 14
        '''
        return F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2

    @staticmethod
    @lru_cache(maxsize=128)
    def improved_fidelity(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) formula (18) page 14
        '''
        return (F ** 2 + ((1 - F) / 3) ** 2) / (F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2)
