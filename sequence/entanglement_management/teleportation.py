"""Teleportation Protocol Implementation
    This module implements the teleportation protocol for quantum communication.   
    It includes the core logic for Alice's and Bob's sides of the teleportation process,
    handling entangled states, and applying corrections based on classical messages.
"""

from enum import Enum, auto
from ..components.circuit import Circuit
from ..message import Message
from ..utils import log
from ..protocol import Protocol
from ..topology.node import DQCNode


class TeleportMsgType(Enum):
    """Enumeration for different types of teleportation messages."""
    MEASUREMENT_RESULT = auto()

class TeleportMessage(Message):
    """Classical message used to convey the Pauli corrections (x, z) from
    sender to receiver during teleportation.

    Attributes:
        idx (int): Index of the memory in the receiver's memory manager.
        x_flip (int): Whether to apply X correction (1 for yes, 0 for no).
        z_flip (int): Whether to apply Z correction (1 for yes, 0 for no).
    """
    def __init__(self, idx: int, x_flip: int, z_flip: int):
        # this app name must match what TeleportApp expects
        super().__init__(TeleportMsgType.MEASUREMENT_RESULT, 'teleport_app')
        self.idx    = idx
        self.x_flip = x_flip
        self.z_flip = z_flip

class TeleportProtocol(Protocol):

    """
    Core teleportation logic:
     - handle_entangled(): invoked when a comm-memory becomes ENTANGLED
     - handle_correction(): invoked when Bob receives Alice's classical bits
    """
    
    _bsm_circuit = Circuit(2)
    _bsm_circuit.cx(0,1)
    _bsm_circuit.h(0)
    _bsm_circuit.measure(0)
    _bsm_circuit.measure(1)

    _z_flip_circuit = Circuit(1)
    _z_flip_circuit.z(0)

    _x_flip_circuit = Circuit(1)
    _x_flip_circuit.x(0)

    def __init__(self, owner: DQCNode, data_src=None):
        """ Initialize the teleportation protocol.
            
        Args:
            owner (QuantumNode): The node that owns this protocol.
            data_src (str): The name of the data source memory to teleport.
        """
        self.owner    = owner
        self.data_src = data_src
        self.name = f"{owner.name}.TeleportProtocol"
        self.pending: dict[int, object] = {}
        log.logger.info(f"[TeleportProtocol:{owner.name}] initialized (data_src={data_src})")

    def start(self):
        """ Start the teleportation protocol.
        This method is called when the protocol is initialized.
        It sets up the necessary components and logs the start of the protocol.
        """
        log.logger.debug(f"[TeleportProtocol:{self.owner.name}] start() called")

    def handle_entangled(self, info, reservation):
        log.logger.debug(f"[TeleportProtocol:{self.owner.name}] handle_entangled idx={info.index}, state={info.state}, initiator={reservation.initiator}")
        if reservation.initiator == self.owner.name:
            log.logger.info(f"[TeleportProtocol:{self.owner.name}] acting as Alice on idx={info.index}")
            self._alice_bell_measure(info, reservation.responder)
        else:
            log.logger.info(f"[TeleportProtocol:{self.owner.name}] stashing Bob comm idx={info.index}")
            self.pending[info.index] = info.memory

    def _alice_bell_measure(self, info, bob_name: str):
        """ Perform Bell measurement on the entangled memory and send corrections to Bob. 

        Args:
            info (MemoryInfo): The memory info containing the entangled state.
            bob_name (str): The name of the Bob node to send corrections to.
        """
        comm_key = info.memory.qstate_key
        data_key = self.owner.components["data_mem"].memories[self.data_src].qstate_key

        log.logger.debug(f"[TeleportProtocol:{self.owner.name}] _alice_bell_measure data_key={data_key}, comm_key={comm_key}")

        rnd  = self.owner.get_generator().random()
        meas = self.owner.timeline.quantum_manager.run_circuit(TeleportProtocol._bsm_circuit, [data_key, comm_key], rnd)
        z, x = meas[data_key], meas[comm_key]
        log.logger.info(f"[TeleportProtocol:{self.owner.name}] Bell measurement idx={info.index} → z={z}, x={x}")

        # send classical corrections to Bob
        msg = TeleportMessage(info.index, x_flip=x, z_flip=z)
        self.owner.send_message(bob_name, msg)
        log.logger.info(f"[TeleportProtocol:{self.owner.name}] sent correction to {bob_name}: idx={info.index}, x={x}, z={z}")

    def received_message(self, src, msg):
        """ Handle incoming messages, specifically teleportation corrections.

        Args:
            src (str): Source of the message.
            msg (TeleportMessage): The teleportation message containing corrections.
        """
        if msg.msg_type == TeleportMsgType.MEASUREMENT_RESULT:
            result = self.handle_correction(msg)
        else:
            log.logger.warning(f"[TeleportProtocol:{self.owner.name}] received unknown message type {msg.type} from {src}")
            
    def handle_correction(self, msg: TeleportMessage):
        """ Handle the classical correction message from Alice.
        Applies the corrections to the entangled memory and notifies the app.

        Args:
            msg (TeleportMessage): The message containing the correction bits.
        """
        log.logger.debug(f"[TeleportProtocol:{self.owner.name}] handle_correction idx={msg.idx}, x_flip={msg.x_flip}, z_flip={msg.z_flip}")
        mem = self.pending.pop(msg.idx, None)
        if mem is None:
            log.logger.warning(f"[TeleportProtocol:{self.owner.name}] no pending comm to correct for idx={msg.idx}")
            return

        key = mem.qstate_key
        log.logger.debug(f"[TeleportProtocol:{self.owner.name}] applying Pauli corrections on key={key}")
        if msg.x_flip:
            rnd = self.owner.get_generator().random()
            self.owner.timeline.quantum_manager.run_circuit(TeleportProtocol._x_flip_circuit, [key], rnd)
            log.logger.info(f"[TeleportProtocol:{self.owner.name}] X-flip applied on idx={msg.idx}")
        if msg.z_flip:
            rnd = self.owner.get_generator().random()
            self.owner.timeline.quantum_manager.run_circuit(TeleportProtocol._z_flip_circuit, [key], rnd)
            log.logger.info(f"[TeleportProtocol:{self.owner.name}] Z-flip applied on idx={msg.idx}")
        
        self.owner.teleport_app.teleport_complete(key)

