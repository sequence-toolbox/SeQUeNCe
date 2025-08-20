from abc import ABC
from enum import Enum, auto
from typing import TYPE_CHECKING, List

from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.utils.log import logger
from ...message import Message

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node


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
        super().__init__(msg_type, receiver)
        try:
            self.meas_res = kwargs['meas_res']
        except KeyError:
            raise ValueError("Missing required argument 'meas_res' for BBPSSWMessage")

    def __str__(self):
        return f"\"BBPSSW: type={self.msg_type}, meas_res={self.meas_res}\""


class BBPSSWProtocolFactory:
    """Factory for creating BBPSSW protocol instances."""
    _registry = {}

    @classmethod
    def register(cls, name, manager_class):
        cls._registry[name] = manager_class

    @classmethod
    def create(cls, name, *args, **kwargs):
        if name not in cls._registry:
            raise ValueError(f"BBPSSW Protocol '{name}' is not registered.")
        return cls._registry[name](*args, **kwargs)


class BBPSSWProtocol(EntanglementProtocol, ABC):
    def __init__(self, owner: "Node", name: str, kept_memo: "Memory", meas_memo: "Memory"):
        """Constructor for purification protocol.

        Args:
            owner (Node): Node the protocol of which the protocol is attached.
            name (str): Name of protocol instance.
            kept_memo (Memory): Memory to keep and improve the fidelity.
            meas_memo (Memory): Memory to measure and discard.
        """
        assert kept_memo != meas_memo
        super().__init__(owner, name)
        self.memories: List[Memory] = [kept_memo, meas_memo]
        self.kept_memo: Memory = kept_memo
        self.meas_memo: Memory = meas_memo
        self.remote_node_name: str = ''
        self.remote_protocol_name: str = ''
        self.remote_memories: List[str] = []
        self.meas_res = None
        if self.meas_memo is None:
            self.memories.pop()

    def is_ready(self) -> bool:
        """Check if the protocol is ready to start."""
        return self.remote_node_name is not None

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance

        args:
            protocol (str): Other protocol name.
            node (str): Other node name.
            memories (List[str]): The list of memory names used on other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol
        self.remote_memories = memories

    def start(self) -> None:
        """Method to start the entanglement purification protocol.

        Side Effects:
            May update parameters of kept memory.
            Will send message to other protocol instance.
        """
        logger.info(f'{self.owner.name} protocol start with partner {self.remote_node_name}')

        # Validation before starting the protocol
        kept_entangled_memo = self.kept_memo.entangled_memory('node_id')
        meas_entangled_memo = self.meas_memo.entangled_memory('node_id')
        assert self.is_ready(), \
            "Protocol is not ready to start. Remote node not set, please use set_others() function to set it."
        assert kept_entangled_memo == meas_entangled_memo, \
            f'Mismatch of entangled memories {kept_entangled_memo} and {meas_entangled_memo} on node {self.owner.name}.'
        assert self.kept_memo.fidelity > 0.5, \
            f'Fidelity of kept memory is too low: {self.kept_memo.fidelity}.'
        assert self.meas_memo.fidelity > 0.5, \
            f'Fidelity of measurement memory is too low: {self.meas_memo.fidelity}.'

    def received_message(self, src: str, msg: BBPSSWMessage) -> None:
        """Method to receive messages.

         args:
            src (str): Name of the node that sent the message.
            msg (BBPSSWMessage): Message received.

         Side Effects:
            Will call `update_resource_manager` method.
         """

        pass

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive memory expiration events.

        args:
            memory (Memory): The memory that has expired.

        Side Effects:
            Will call `update_resource_manager` method.
        """
        assert memory in self.memories, \
            f'Memory {memory.name} is not part of this protocol instance.'

        if self.meas_memo is None:
            self.update_resource_manager(memory, 'RAW')
        else:
            for memory in self.memories:
                self.update_resource_manager(memory, 'RAW')

    def release(self) -> None:
        pass
