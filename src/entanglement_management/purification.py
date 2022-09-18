"""Code for BBPSSW entanglement purification.

This module defines code to support the BBPSSW protocol for entanglement purification.
Success results are pre-determined based on network parameters.
Also defined is the message type used by the BBPSSW code.
"""

from enum import Enum, auto
from typing import List, TYPE_CHECKING
from functools import lru_cache

if TYPE_CHECKING:
    from ..components.memory import Memory
    from ..topology.node import Node

from ..message import Message
from .entanglement_protocol import EntanglementProtocol
from ..utils import log
from ..components.circuit import Circuit


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
            self.meas_res = kwargs['meas_res']
        else:
            raise Exception("BBPSSW protocol create unknown type of message: %s" % str(msg_type))


class BBPSSW(EntanglementProtocol):
    """Purification protocol instance.

    This class provides an implementation of the BBPSSW purification protocol.
    It should be instantiated on a quantum router node.

    Variables:
        BBPSSW.circuit (Circuit): circuit that purifies entangled memories.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        kept_memo: memory to be purified by the protocol (should already be entangled).
        meas_memo: memory to measure and discart (should already be entangled).
        meas_res (int): measurement result from circuit.
        remote_node_name (str): name of other node.
        remote_protocol_name (str): name of other protocol
        remote_memories (List[str]): name of remote memories
    """

    circuit = Circuit(2)
    circuit.cx(0, 1)
    circuit.measure(1)

    def __init__(self, own: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory"):
        """Constructor for purification protocol.

        Args:
            own (Node): node protocol is attached to.
            name (str): name of protocol instance.
            kept_memo (Memory): memory to have fidelity improved.
            meas_memo (Memory): memory to measure and discard.
        """

        assert kept_memo != meas_memo
        EntanglementProtocol.__init__(self, own, name)
        self.memories: List[Memory] = [kept_memo, meas_memo]
        self.kept_memo: Memory = kept_memo
        self.meas_memo: Memory = meas_memo
        self.remote_node_name: str = None
        self.remote_protocol_name: str = None
        self.remote_memories: List[str] = None
        self.meas_res = None
        if self.meas_memo is None:
            self.memories.pop()

    def is_ready(self) -> bool:
        return self.remote_node_name is not None

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol
        self.remote_memories = memories

    def start(self) -> None:
        """Method to start entanglement purification.

        Run the circuit below on two pairs of entangled memories on both sides of protocol.

        o -------(x)----------| M |
        .         |
        .   o ----.----------------
        .   .
        .   .
        .   o
        .
        o

        The overall circuit is shown below:

         o -------(x)----------| M |
         .         |
         .   o ----.----------------
         .   .
         .   .
         .   o ----.----------------
         .         |
         o -------(x)----------| M |

        Side Effects:
            May update parameters of kept memory.
            Will send message to other protocol instance.
        """

        log.logger.info(f"{self.own.name} protocol start with partner {self.remote_node_name}")

        assert self.is_ready(), "other protocol is not set; please use set_others function to set it."
        kept_memo_ent = self.kept_memo.entangled_memory["node_id"]
        meas_memo_ent = self.meas_memo.entangled_memory["node_id"]
        assert kept_memo_ent == meas_memo_ent, "mismatch of entangled memories {}, {} on node {}".format(
            kept_memo_ent, meas_memo_ent, self.own.name)
        assert self.kept_memo.fidelity == self.meas_memo.fidelity > 0.5

        meas_samp = self.own.get_generator().random()
        self.meas_res = self.own.timeline.quantum_manager.run_circuit(
            self.circuit, [self.kept_memo.qstate_key,
                           self.meas_memo.qstate_key],
            meas_samp)
        self.meas_res = self.meas_res[self.meas_memo.qstate_key]
        dst = self.kept_memo.entangled_memory["node_id"]

        message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES,
                                self.remote_protocol_name,
                                meas_res=self.meas_res)
        self.own.send_message(dst, message)

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Method to receive messages.

        Args:
            src (str): name of node that sent the message.
            msg (BBPSSW message): message received.

        Side Effects:
            Will call `update_resource_manager` method.
        """

        log.logger.info(
            self.own.name + " received result message, succeeded: {}".format(
                self.meas_res == msg.meas_res))
        assert src == self.remote_node_name

        self.update_resource_manager(self.meas_memo, "RAW")
        if self.meas_res == msg.meas_res:
            self.kept_memo.fidelity = BBPSSW.improved_fidelity(self.kept_memo.fidelity)
            self.update_resource_manager(self.kept_memo, state="ENTANGLED")
        else:
            self.update_resource_manager(self.kept_memo, state="RAW")

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive memory expiration events.

        Args:
            memory (Memory): memory that has expired.

        Side Effects:
            Will call `update_resource_manager` method.
        """

        assert memory in self.memories
        if self.meas_memo is None:
            self.update_resource_manager(memory, "RAW")
        else:
            for memory in self.memories:
                self.update_resource_manager(memory, "RAW")

    def release(self) -> None:
        pass

    @staticmethod
    @lru_cache(maxsize=128)
    def improved_fidelity(F: float) -> float:
        """Method to calculate fidelity after purification.
        
        Formula comes from Dur and Briegel (2007) formula (18) page 14.

        Args:
            F (float): fidelity of entanglement.
        """

        return (F ** 2 + ((1 - F) / 3) ** 2) / (F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2)
