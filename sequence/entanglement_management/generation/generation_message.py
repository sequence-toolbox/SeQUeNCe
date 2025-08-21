from enum import auto, Enum
from typing import TYPE_CHECKING, Any

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
        res (int): detector number at BSM node (if `msg_type == MEAS_RES`).
        time (int): detection time at BSM node (if `msg_type == MEAS_RES`).
        resolution (int): time resolution of BSM detectors (if `msg_type == MEAS_RES`).
    """

    def __init__(self, msg_type: GenerationMsgType, receiver: str, protocol_type: EntanglementProtocol, **kwargs):
        super().__init__(msg_type, receiver)
        self.protocol_type = protocol_type

        if msg_type is GenerationMsgType.NEGOTIATE:
            self.qc_delay = kwargs.get("qc_delay")
            self.frequency = kwargs.get("frequency")

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:
            self.emit_time = kwargs.get("emit_time")

        elif msg_type is GenerationMsgType.MEAS_RES:
            self.detector = kwargs.get("detector")
            self.time = kwargs.get("time")
            self.resolution = kwargs.get("resolution")

        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(msg_type))

    def __repr__(self):
        if self.msg_type is GenerationMsgType.NEGOTIATE:
            return "type:{}, qc_delay:{}, frequency:{}".format(self.msg_type, self.qc_delay, self.frequency)
        elif self.msg_type is GenerationMsgType.NEGOTIATE_ACK:
            return "type:{}, emit_time:{}".format(self.msg_type, self.emit_time)
        elif self.msg_type is GenerationMsgType.MEAS_RES:
            return "type:{}, detector:{}, time:{}, resolution={}".format(self.msg_type, self.detector,
                                                                         self.time, self.resolution)
        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(self.msg_type))
