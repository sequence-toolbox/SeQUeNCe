"""Definition of the Network Manager.

This module defines the NetworkManager class, an implementation of the SeQUeNCe network management module.
Also included in this module is the message type used by the network manager and a function for generating network managers with default protocols.
"""
from sequence.utils.log import logger
from abc import abstractmethod, ABC
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from ..components.memory import MemoryArray

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..protocol import StackProtocol

from ..message import Message
from ..protocol import Protocol
from .routing_distributed import DistributedRoutingProtocol
from .routing_static import StaticRoutingProtocol
from .forwarding import ForwardingProtocol
from .reservation import ResourceReservationProtocol, ResourceReservationMessage, RSVPMsgType, MemoryTimeCard
from ..utils import log

class NetworkManagerMessageType(Enum):
    """Network manager message type used by the network manager.
    """
    REQUEST = auto()
    APPROVE = auto()
    REJECT = auto()


class NetworkManagerMessage(Message):
    """Message used by the network manager.

    Attributes:
        msg_type (Enum): message type required by base message type.
        receiver (str): name of destination protocol instance.
        payload (Message): message to be passed through destination network manager.
    """

    def __init__(self, msg_type: Enum, receiver: str, payload):
        super().__init__(msg_type, receiver)
        self.payload = payload

    def __str__(self) -> str:
        return f"type={self.msg_type}; receiver={self.receiver}; payload={self.payload}"


class NetworkManager(ABC):
    """Network Manager Abstraction
    Has the following responsibilities: Take in a reservation request, complete scheduling in some manner, receive the
    decided path, and finally inform the ResourceManager to create Rules."""
    _registry: dict[str, type['NetworkManager']] = {}
    _global_type: str = 'distributed'

    def __init__(self, owner: QuantumRouter, memory_array_name: str, **kwargs):
        if kwargs:
            logger.warning(f'Network Manager ABC received kwargs: {list(kwargs.keys())}, ignoring.')
        self.name: str = 'network_manager'
        self.owner = owner
        self.memory_array_name = memory_array_name
        self.memo_arr: MemoryArray = owner.components[memory_array_name]
        self.timecards: list[MemoryTimeCard] = [MemoryTimeCard(i) for i in range(len(self.memo_arr))]

    @classmethod
    def register(cls, name, network_manager_cls=None):
        if network_manager_cls is not None:
            cls._registry[name] = network_manager_cls
            return None

        def decorator(network_manager_cls_dec: type['NetworkManager']):
            cls._registry[name] = network_manager_cls_dec
            return network_manager_cls_dec
        return decorator

    @classmethod
    def create(cls, owner, memory_array_name: str, **kwargs: Any) -> 'NetworkManager':
        network_manager_cls: type['NetworkManager'] = cls._registry[cls._global_type]
        return network_manager_cls(owner, memory_array_name, **kwargs)

    @classmethod
    def set_global_type(cls, network_manager_type: str) -> None:
        if network_manager_type not in cls._registry:
            raise ValueError(f'Network Manager {network_manager_type} is not registered.')
        else:
            cls._global_type = network_manager_type


    @abstractmethod
    def received_message(self, src: str, msg: NetworkManagerMessage):
        """Handle Message received into the NetworkManager."""
        pass

    @abstractmethod
    def request(self, responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity):
        """Handle Requests from the Application."""
        pass

    def push(self, dst: str, msg: NetworkManagerMessage):
        self.owner.send_message(dst, msg)

    def get_timecards(self):
        return self.timecards