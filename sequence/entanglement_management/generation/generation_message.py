from enum import auto, Enum
from typing import TYPE_CHECKING, Any, Type, Optional

from ..entanglement_protocol import EntanglementProtocol
from ...message import Message


def valid_trigger_time(trigger_time: int, target_time: int, resolution: int) -> bool:
    """return True if the trigger time is valid, else return False."""
    lower = target_time - (resolution // 2)
    upper = target_time + (resolution // 2)
    return lower <= trigger_time <= upper


class GenerationMsgType(Enum):
    """Defines possible message types for entanglement generation."""

    NEGOTIATE = auto()
    NEGOTIATE_ACK = auto()
    MEAS_RES = auto()


class EntanglementGenerationMessage(Message):
    """Message used by entanglement generation protocols.

    This message contains all information passed between generation protocol instances.
    Messages of different types contain different information.

    Attributes:
        msg_type (GenerationMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        qc_delay (int): quantum channel delay to BSM node (if `msg_type == NEGOTIATE`).
        frequency (float): frequency with which local memory can be excited (if `msg_type == NEGOTIATE`).
        emit_time (int): time to emit photon for measurement (if `msg_type == NEGOTIATE_ACK`).
        detector (int): detector number at BSM node (if `msg_type == MEAS_RES`).
        time (int): detection time at BSM node (if `msg_type == MEAS_RES`).
        resolution (int): time resolution of BSM detectors (if `msg_type == MEAS_RES`).
    """

    def __init__(self, msg_type: GenerationMsgType, receiver: str | None, protocol_type: Type[EntanglementProtocol],
                 **kwargs):
        super().__init__(msg_type, receiver)
        self.protocol_type = protocol_type

        self.qc_delay: Optional[int] = None
        self.frequency: Optional[float] = None
        self.emit_time: Optional[int] = None
        self.detector: Optional[int] = None
        self.time: Optional[int] = None
        self.resolution: Optional[int] = None

        match msg_type:
            case GenerationMsgType.NEGOTIATE:
                self.qc_delay = kwargs.get("qc_delay")
                self.frequency = kwargs.get("frequency")

            case GenerationMsgType.NEGOTIATE_ACK:
                self.emit_time = kwargs.get("emit_time")

            case GenerationMsgType.MEAS_RES:
                self.detector = kwargs.get("detector")
                self.time = kwargs.get("time")
                self.resolution = kwargs.get("resolution")
            case _:
                raise Exception(f'EntanglementGeneration generated invalid message type {msg_type}')

    def __repr__(self):
        match self.msg_type:
            case GenerationMsgType.NEGOTIATE:
                return f'type: {self.msg_type}, qc_delay: {self.qc_delay}, frequency: {self.frequency}'
            case GenerationMsgType.NEGOTIATE_ACK:
                return f'type: {self.msg_type}, emit_time: {self.emit_time}'
            case GenerationMsgType.MEAS_RES:
                return f'type: {self.msg_type}, detector: {self.detector}, time: {self.time}, resolution: {self.resolution}'
            case _:
                raise Exception(f'EntanglementGeneration generated invalid message type {self.msg_type}')