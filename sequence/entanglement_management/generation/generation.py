from __future__ import annotations

from abc import ABC
from math import sqrt
from typing import TYPE_CHECKING, List, Dict, Type, Any

from sequence.topology.node import BSMNode
from .generation_message import EntanglementGenerationMessage, GenerationMsgType
from ...resource_management.memory_manager import MemoryInfo

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology import Node
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

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", **kwargs):
        super().__init__(owner, name)
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

        # Memory Internal Info
        self.ent_round = 0
        self.bsm_res = [0, 0]

        self.scheduled_events = []

        # Misc.
        self.primary: bool = False
        self.debug: bool = False
        self._qstate_key: int = self.memory.qstate_key


    @classmethod
    def register(cls, name: str, protocol_class: Type['EntanglementGenerationA'] = None):
        if protocol_class is not None:
            cls._registry['name'] = protocol_class
            return None

        def decorator(protocol_class: Type['EntanglementGenerationA']):
            cls._registry[name] = protocol_class
            return protocol_class
        return decorator

    @classmethod
    def create(cls, owner: "Node", name: str, middle: str, other: str, memory: "Memory", **kwargs) -> 'EntanglementGenerationA':
        try:
            protocol_class = cls._registry[name]
            return protocol_class(owner, name, middle, other, memory, **kwargs)
        except KeyError:
            raise ValueError(f"Protocol class '{name}' is not registered.")

    @classmethod
    def list_protocols(cls) -> List[str]:
        """List all registered EntanglementGenerationA protocols."""
        return list(cls._registry.keys())

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        assert self.remote_protocol_name != '', \
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
                                                    protocol_type=self,
                                                    qc_delay=self.qc_delay,
                                                    frequency=frequency)
            self.owner.send_message(self.remote_node_name, message)

    def update_memory(self) -> bool | None:
        pass

    def emit_event(self) -> None:
        pass

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        pass

    def is_ready(self) -> bool:
        return self.remote_protocol_name != ''

    def memory_expire(self, memory: "Memory") -> None:
        assert memory == self.memory, \
            "Memory to expire does not match the protocol's memory"
        self.update_resource_manager(memory, MemoryInfo.RAW)
        for event in self.scheduled_events:
            if event.time >= self.owner.timeline.now():
                self.owner.timeline.remove_event(event)

    def _entanglement_succeed(self):
        log.logger.info(f'{self.owner.name} successful entanglement of memory {self.memory}')
        self.memory.entangled_memory['node_id'] = self.remote_node_name
        self.memory.entangled_memory['memo_id'] = self.remote_memo_id

    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(f'{self.owner.name} failed entanglement of memory {self.memory}')

        self.update_resource_manager(self.memory, MemoryInfo.RAW)


class EntanglementGenerationB(EntanglementProtocol, ABC):
    _registry: Dict[str, Type['EntanglementGenerationB']] = {}

    def __init__(self, owner: "BSMNode", name: str, others: List[str], **kwargs) -> None:
        super().__init__(owner, name)
        assert len(others) == 2
        self.others = others


    @classmethod
    def register(cls, name: str, protocol_class: Type['EntanglementGenerationB'] = None):
        if protocol_class is not None:
            cls._registry['name'] = protocol_class
            return None

        def decorator(protocol_class: Type['EntanglementGenerationB']):
            cls._registry[name] = protocol_class
            return protocol_class
        return decorator

    @classmethod
    def create(cls, owner: "Node", name: str, others, **kwargs) -> 'EntanglementGenerationB':
        try:
            protocol_class = cls._registry[name]
            return protocol_class(owner, name, others, **kwargs)
        except KeyError:
            raise ValueError(f"Protocol class '{name}' is not registered.")

    @classmethod
    def list_protocols(cls) -> List[str]:
        """List all registered EntanglementGenerationA protocols."""
        return list(cls._registry.keys())

    def bsm_update(self, bsm, info: Dict['str', Any]) -> None:
        assert info['info_type'] == "BSM_res"

        res = info["res"]
        time = info["time"]
        resolution = bsm.resolution

        for node in self.others:
            message = EntanglementGenerationMessage(GenerationMsgType.MEAS_RES,
                                                    receiver=None,  # receiver is None (not paired)
                                                    protocol_type=EntanglementGenerationA,
                                                    detector=res,
                                                    time=time,
                                                    resolution=resolution)
            self.owner.send_message(node, message)

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