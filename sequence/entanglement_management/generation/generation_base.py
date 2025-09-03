from abc import ABC, abstractmethod
from math import sqrt
from typing import TYPE_CHECKING, List, Dict, Type, Any

from .generation_message import EntanglementGenerationMessage, GenerationMsgType
from ...resource_management.memory_manager import MemoryInfo
from ...constants import BARRET_KOK

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node, BSMNode

from ..entanglement_protocol import EntanglementProtocol
from ...components.circuit import Circuit
from ...utils import log


class QuantumCircuitMixin:
    _plus_state = [sqrt(1 / 2), sqrt(1 / 2)]
    _flip_circuit = Circuit(1)
    _flip_circuit.x(0)
    _z_circuit = Circuit(1)
    _z_circuit.z(0)


class EntanglementGenerationA(EntanglementProtocol, ABC):
    _registry: Dict[str, Type['EntanglementGenerationA']] = {}
    _global_type: str = BARRET_KOK

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", **kwargs):
        super().__init__(owner, name)
        self.protocol_type = BARRET_KOK
        self.middle: str = middle
        self.remote_node_name: str = other
        self.remote_protocol_name: str = ''

        # Memory Info
        self.memory: Memory = memory
        self.memories: List[Memory] = [memory]
        self.remote_memo_id: str = ''

        # Network and Hardware Info
        self.qc_delay: int = 0
        self.expected_time: int = -1
        self.fidelity: float = memory.raw_fidelity

        # Memory Internal Info
        self.ent_round = 0
        self.bsm_res = [-1, -1]

        self.scheduled_events = []

        # Misc.
        self.primary: bool = False
        self._qstate_key: int = self.memory.qstate_key

    @classmethod
    def set_global_type(cls, protocol_type: str) -> None:
        if protocol_type not in cls._registry:
            raise ValueError(f"Protocol type '{protocol_type}' is not registered.")
        cls._global_type = protocol_type

    @classmethod
    def get_global_type(cls) -> str:
        return cls._global_type

    @classmethod
    def register(cls, name: str, protocol_class: Type['EntanglementGenerationA'] = None):
        if protocol_class is not None:
            cls._registry[name] = protocol_class
            return None

        def decorator(protocol_cls: Type['EntanglementGenerationA']):
            cls._registry[name] = protocol_cls
            return protocol_cls

        return decorator

    @classmethod
    def create(cls, owner: "Node", name: str, middle: str, other: str, memory: "Memory", **kwargs) -> 'EntanglementGenerationA':
        protocol_name = cls.get_global_type()
        try:
            protocol_class = cls._registry[protocol_name]
            return protocol_class(owner, name, middle, other, memory, **kwargs)
        except KeyError:
            raise ValueError(f"Protocol class '{protocol_name}' is not registered.")

    @classmethod
    def clear_global(cls):
        cls._global_type = BARRET_KOK

    @classmethod
    def list_protocols(cls) -> List[str]:
        """List all registered EntanglementGenerationA protocols."""
        return list(cls._registry.keys())

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        assert self.remote_protocol_name == '', \
            "Remote protocol name has been set before, cannot set again."

        self.remote_protocol_name = protocol
        self.remote_memo_id = memories[0]
        self.primary = self.owner.name > self.remote_node_name

    def start(self) -> None:
        """Method to start "one round" in the entanglement generation protocol (there are two rounds in Barrett-Kok).

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        if self not in self.owner.protocols:
            return

        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE,
                                                    self.remote_protocol_name,
                                                    protocol_type=self.protocol_type,
                                                    qc_delay=self.qc_delay,
                                                    frequency=frequency)
            self.owner.send_message(self.remote_node_name, message)

    def update_memory(self) -> bool | None:
        """Update memory state. Must be implemented in a subclass"""
        raise NotImplementedError

    @abstractmethod
    def emit_event(self) -> None:
        """Must be implemented in a subclass"""
        raise NotImplementedError

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        """Must be implemented in a subclass"""
        raise NotImplementedError

    def is_ready(self) -> bool:
        return self.remote_protocol_name != ''

    def memory_expire(self, memory: "Memory") -> None:
        assert memory == self.memory, \
            "Memory to expire does not match the protocol's memory"
        self.update_resource_manager(memory, MemoryInfo.RAW)
        for event in self.scheduled_events:
            if event.time >= self.owner.timeline.now():
                self.owner.timeline.remove_event(event)

    @abstractmethod
    def _entanglement_succeed(self):
        raise NotImplementedError("This method must be implemented in a subclass")

    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(f'{self.owner.name} failed entanglement of memory {self.memory}')

        self.update_resource_manager(self.memory, MemoryInfo.RAW)


class EntanglementGenerationB(EntanglementProtocol, ABC):
    _registry: Dict[str, Type['EntanglementGenerationB']] = {}
    _global_type: str = BARRET_KOK

    def __init__(self, owner: "BSMNode", name: str, others: List[str], **kwargs) -> None:
        super().__init__(owner, name)
        self.protocol_type = BARRET_KOK
        assert len(others) == 2
        self.others = others

    @classmethod
    def set_global_type(cls, protocol_type: str) -> None:
        if protocol_type not in cls._registry:
            raise ValueError(f"Protocol type '{protocol_type}' is not registered.")
        cls._global_type = protocol_type

    @classmethod
    def get_global_type(cls) -> str:
        return cls._global_type

    @classmethod
    def register(cls, name: str, protocol_class: Type['EntanglementGenerationB'] = None):
        if protocol_class is not None:
            cls._registry[name] = protocol_class
            return None

        def decorator(protocol_class: Type['EntanglementGenerationB']):
            cls._registry[name] = protocol_class
            return protocol_class

        return decorator

    @classmethod
    def create(cls, owner: "BSMNode", name: str, others, **kwargs) -> 'EntanglementGenerationB':
        protocol_name: str = cls.get_global_type()
        try:
            protocol_class = cls._registry[protocol_name]
            return protocol_class(owner, name, others, **kwargs)
        except KeyError:
            raise ValueError(f"Protocol class '{protocol_name}' is not registered.")

    @classmethod
    def list_protocols(cls) -> List[str]:
        """List all registered EntanglementGenerationA protocols."""
        return list(cls._registry.keys())

    def bsm_update(self, bsm, info: Dict['str', Any]) -> None:
        """Must be implemented in a subclass"""
        raise NotImplementedError

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        pass

    def start(self) -> None:
        pass

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        raise Exception(f'EntanglementGenerationB protocol {self.name} should not receive message;.')

    def is_ready(self) -> bool:
        return True

    def memory_expire(self, memory: "Memory") -> None:
        raise Exception(f'EntanglementGenerationB protocol {self.name} should not receive memory expiration;.')
