"""The base class for entanglement swapping protocol.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING

from ..entanglement_protocol import EntanglementProtocol
from ...constants import KET_VECTOR_FORMALISM
from ...message import Message
from ...resource_management.memory_manager import MemoryInfo
from ...utils import log

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node


class SwappingMsgType(Enum):
    """Defines possible message types for entanglement generation.
    """
    SWAP_RES = auto()


class EntanglementSwappingMessage(Message):
    """Message used by entanglement swapping protocols.

    This message contains all information passed between swapping protocol instances.

    Attributes:
        msg_type (SwappingMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        fidelity (float): fidelity of the newly swapped memory pair.
        remote_node (str): name of the distant node holding the entangled memory of the new pair.
        remote_memo (int): index of the entangled memory on the remote node.
        expire_time (int): expiration time of the new memory pair.
    """

    def __init__(self, msg_type: SwappingMsgType, receiver: str, **kwargs):
        Message.__init__(self, msg_type, receiver)
        if self.msg_type is SwappingMsgType.SWAP_RES:
            self.fidelity = kwargs.get("fidelity")
            self.remote_node = kwargs.get("remote_node")
            self.remote_memo = kwargs.get("remote_memo")
            self.expire_time = kwargs.get("expire_time")
            self.meas_res = kwargs.get("meas_res")
        else:
            raise Exception("Entanglement swapping protocol create unkown type of message: %s" % str(msg_type))

    def __str__(self):
        if self.msg_type == SwappingMsgType.SWAP_RES:
            return "EntanglementSwappingMessage: msg_type: {}; fidelity: {:.2f}; remote_node: {}; remote_memo: {}; ".format(
                self.msg_type, self.fidelity, self.remote_node, self.remote_memo)


class EntanglementSwappingA(EntanglementProtocol, ABC):
    """Base class for Entanglement Swapping A protocol.

        The default formalism is KET_VECTOR_FORMALISM.
    """
    _registry: dict[str, type['EntanglementSwappingA']] = {}
    _global_formalism: str = KET_VECTOR_FORMALISM

    def __init__(self, owner: "Node", name: str, left_memo: "Memory", right_memo: "Memory", success_prob: float = 1):
        """Constructor for Entanglement Swapping A protocol.

        Args:
            owner (Node): node that protocol instance is attached to.
            name (str): label for protocol instance.
            left_memo (Memory): memory entangled with a memory on one distant node.
            right_memo (Memory): memory entangled with a memory on the other distant node.
            success_prob (float): probability of a successful swapping operation (default 1).
        """
        assert left_memo != right_memo
        super().__init__(owner, name, 'EntanglementSwappingA')
        self.memories = [left_memo, right_memo]
        self.left_memo = left_memo
        self.right_memo = right_memo
        self.left_node = left_memo.entangled_memory['node_id']
        self.left_remote_memo = left_memo.entangled_memory['memo_id']
        self.right_node = right_memo.entangled_memory['node_id']
        self.right_remote_memo = right_memo.entangled_memory['memo_id']
        self.success_prob = success_prob
        assert 1 >= self.success_prob >= 0, "Entanglement swapping success probability must be between 0 and 1."
        self.is_success = False
        self.left_protocol_name = None
        self.right_protocol_name = None

    @classmethod
    def set_formalism(cls, formalism: str) -> None:
        """Set the global formalism for all Entanglement Swapping A protocol instances.

        Args:
            formalism (str): global formalism for all Entanglement Swapping A protocol instances.
        """
        if formalism not in cls._registry:
            raise ValueError(f"Protocol type {formalism} not found in registry.")
        cls._global_formalism = formalism

    @classmethod
    def get_formalism(cls) -> str:
        """Get the global formalism for all Entanglement Swapping A protocol instances.

        Returns:
            The global formalism for all Entanglement Swapping A protocol instances.
        """
        return cls._global_formalism

    @classmethod
    def register(cls, name: str, protocol_class: type['EntanglementSwappingA'] = None
                 ) -> Callable[[type['EntanglementSwappingA']], type['EntanglementSwappingA']] | None:
        """Register a specific type of Entanglement Swapping A protocol.

        This method should be used as a decorator to register different types of Entanglement Swapping A protocols.
        The registered protocol can then be set as the global formalism for all Entanglement Swapping A protocol instances.

        Args:
            name (str): name of the specific type of Entanglement Swapping A protocol.
            protocol_class (type[EntanglementSwappingA] | None): the class of the specific type of Entanglement Swapping A protocol. If None, the decorated class will be registered.

        Returns:
            If protocol_class is None, returns a decorator function. Otherwise, returns None.
        """
        if name in cls._registry:
            raise ValueError(f"Protocol type {name} already registered.")

        if protocol_class is not None:
            cls._registry[name] = protocol_class
            return None

        def decorator(protocol_class: type['EntanglementSwappingA']) -> type['EntanglementSwappingA']:
            if name in cls._registry:
                raise ValueError(f"Protocol type {name} already registered.")
            cls._registry[name] = protocol_class
            return protocol_class
        
        return decorator

    @classmethod
    def create(cls, owner: "Node", name: str, left_memo: "Memory", right_memo: "Memory", 
               success_prob: float = 1, **kwargs) -> 'EntanglementSwappingA':
        """Factory method to create an Entanglement Swapping A protocol instance of the global formalism.

        Args:
            owner (Node): node that protocol instance is attached to.
            name (str): label for protocol instance.
            left_memo (Memory): memory entangled with a memory on one distant node.
            right_memo (Memory): memory entangled with a memory on the other distant node.
            success_prob (float): probability of a successful swapping operation (default 1).

        Returns:
            An instance of the Entanglement Swapping A protocol of the global formalism.
        """
        protocol_name = EntanglementSwappingA.get_formalism()
        try:
            protocol_class = cls._registry[protocol_name]
            return protocol_class(owner, name, left_memo, right_memo, success_prob, **kwargs)
        except KeyError:
            raise ValueError(f"Protocol class '{protocol_name}' is not registered.")

    @classmethod
    def list_protocols(cls) -> list[str]:
        """List all registered Entanglement Swapping A protocols.

        Returns:
            A list of names of all registered Entanglement Swapping A protocols.
        """
        return list(cls._registry.keys())

    @classmethod
    def clear_global_formalism(cls) -> None:
        """Resets the global formalism to default"""
        cls._global_formalism = KET_VECTOR_FORMALISM

    def is_ready(self) -> bool:
        """Check if the protocol is ready.
        
        Returns:
            bool: True if the protocol is ready to start, False otherwise.
        """
        return (self.left_protocol_name is not None) and (self.right_protocol_name is not None)
    
    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (list[str]): the list of memories name used on other node.
        """
        if node == self.left_memo.entangled_memory["node_id"]:
            self.left_protocol_name = protocol
        elif node == self.right_memo.entangled_memory["node_id"]:
            self.right_protocol_name = protocol
        else:
            raise Exception("Cannot pair protocol %s with %s" % (self.name, protocol))

    def success_probability(self) -> float:
        """A simple model for BSM success probability.

        Returns:             
            float: the probability of a successful swapping operation.
        """
        return self.success_prob

    @abstractmethod
    def start(self) -> None:
        """Method to start entanglement swapping process (abstract).
        """
        pass

    def received_message(self, src: str, msg: Message) -> None:
        """Method to receive messages (should not be used on A protocol).
        """
        raise Exception("EntanglementSwappingA protocol '{}' should not receive messages.".format(self.name))

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive memory expiration events.

        Releases held memories on current node.
        Memories at the remote node are released as well.

        Args:
            memory (Memory): memory that expired.

        Side Effects:
            Will invoke `update` method of attached resource manager.
            Will invoke `release_remote_protocol` or `release_remote_memory` method of resource manager.
        """
        assert self.is_ready() is False
        if self.left_protocol_name:
            self.release_remote_protocol(self.left_node)
        else:
            self.release_remote_memory(self.left_node, self.left_remote_memo)
        if self.right_protocol_name:
            self.release_remote_protocol(self.right_node)
        else:
            self.release_remote_memory(self.right_node, self.right_remote_memo)

        for memo in self.memories:
            if memo == memory:
                self.update_resource_manager(memo, MemoryInfo.RAW)
            else:
                self.update_resource_manager(memo, MemoryInfo.ENTANGLED)

    def release_remote_protocol(self, remote_node: str):
        self.owner.resource_manager.release_remote_protocol(remote_node, self)

    def release_remote_memory(self, remote_node: str, remote_memo: str):
        self.owner.resource_manager.release_remote_memory(remote_node, remote_memo)


class EntanglementSwappingB(EntanglementProtocol, ABC):
    """Base class for Entanglement Swapping B protocol.

        The default formalism is KET_VECTOR_FORMALISM.
    """
    _registry: dict[str, type['EntanglementSwappingB']] = {}
    _global_formalism: str = KET_VECTOR_FORMALISM

    def __init__(self, owner: "Node", name: str, hold_memo: "Memory"):
        """Constructor for entanglement swapping B protocol.

        Args:
            owner (Node): node protocol instance is attached to.
            name (str): name of protocol instance.
            hold_memo (Memory): memory entangled with a memory on middle node.
        """
        super().__init__(owner, name, 'EntanglementSwappingB')
        self.memories = [hold_memo]
        self.memory = hold_memo
        self.remote_protocol_name = None
        self.remote_node_name = None

    @classmethod
    def set_formalism(cls, formalism: str) -> None:
        """Set the global formalism for all Entanglement Swapping B protocol instances.
        
        Valid Built-formalisms:
            1. Bell Diagonal -> bds
            2. Circuit -> circuit (DEFAULT)

        Args:
            formalism (str): global formalism for all Entanglement Swapping B protocol instances.
        """
        if formalism not in cls._registry:
            raise ValueError(f"Protocol type {formalism} not found in registry.")
        cls._global_formalism = formalism

    @classmethod
    def get_formalism(cls) -> str:
        """Get the global formalism for all Entanglement Swapping B protocol instances.

        Returns:
            The global formalism for all Entanglement Swapping B protocol instances.
        """
        return cls._global_formalism

    @classmethod
    def register(cls, name: str, protocol_class: type['EntanglementSwappingB'] = None
                 ) -> Callable[[type['EntanglementSwappingB']], type['EntanglementSwappingB']] | None:
        """Register a specific type of Entanglement Swapping B protocol.

        This method should be used as a decorator to register different types of Entanglement Swapping B protocols.

        Args:
            name (str): name of the specific type of Entanglement Swapping B protocol.
            protocol_class (type[EntanglementSwappingB] | None): the class of the specific type of Entanglement Swapping B protocol. If None, the decorated class will be registered.

        Returns:
            If protocol_class is None, returns a decorator function. Otherwise, returns None.
        """
        if name in cls._registry:
            raise ValueError(f"{name} already registered.")

        if protocol_class is not None:
            cls._registry[name] = protocol_class
        
        def decorator(protocol_class: type['EntanglementSwappingB']) -> type['EntanglementSwappingB']:
            if name in cls._registry:
                raise ValueError(f"{name} already registered.")
            cls._registry[name] = protocol_class
            return protocol_class

        return decorator

    @classmethod
    def create(cls, owner: "Node", name: str, hold_memo: "Memory", **kwargs) -> 'EntanglementSwappingB':
        """Factory method to create an Entanglement Swapping B protocol instance of the global formalism.
        """
        protocol_name = EntanglementSwappingB.get_formalism()
        try:
            protocol_class = cls._registry[protocol_name]
            return protocol_class(owner, name, hold_memo, **kwargs)
        except KeyError:
            raise ValueError(f"Protocol class '{protocol_name}' is not registered.")

    def is_ready(self) -> bool:
        return self.remote_protocol_name is not None

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (list[str]): the list of memory names used on other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol

    def start(self) -> None:
        log.logger.info(f"{self.owner.name} end protocol start with partner {self.remote_node_name}")

    def memory_expire(self, memory: Memory) -> None:
        """Method to deal with expired memories.

        Args:
            memory (Memory): memory that expired.

        Side Effects:
            Will update memory in attached resource manager.
        """

        self.update_resource_manager(self.memory, MemoryInfo.RAW)

    def release(self) -> None:
        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)

    @abstractmethod
    def received_message(self, src: str, msg: EntanglementSwappingMessage) -> None:
        """Method to receive messages from EntanglementSwappingA.

        Args:
            src (str): name of node sending message.
            msg (EntanglementSwappingMessage): message sent.
        """
        pass

