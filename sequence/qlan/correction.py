from ..components.circuit import Circuit
from ..components.memory import Memory
from ..topology.node import Node
from ..entanglement_management.entanglement_protocol import EntanglementProtocol
from ..message import Message
from ..utils import log
from ..kernel.timeline import Timeline
from .measurement import QlanMeasurementMsgType, QlanB0MsgType

from enum import Enum, auto


class QlanCorrectionMsgType(Enum):
    ACK_Outcome0 = auto()
    ACK_Outcome1 = auto()


class QlanCorrectionProtocol(EntanglementProtocol):
    """This class provides the protocol for the correction after the measurements performed at the QLAN Orchestrator node. 
    It should be instantiated at a client node.

    Attributes:
        circuit (Circuit): Circuit that performs the corrections.
        owner (Node): Node that protocol instance is attached to.
        name (str): Label for protocol instance.
        tl (Timeline): Timeline for protocol scheduling.
        local_memories (list[Memory]): Memories at the orchestrator.
        remote_node_names (list[str]): Names of the remote nodes.
        remote_protocol_names (list[str]): Names of the remote protocols.
        remote_memories (list[list[str]]): Names of the remote memories.
        received_messages (list[Message]): list of received messages.
        sent_messages (list[Message]): list of sent messages.
        B0 (bool): Flag indicating if B0 designation is received.
    """

    def __init__(self, owner: "Node", name: str, tl: "Timeline", local_memories: list[Memory]):
        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.B0 = False
        
        self.local_memories: list[Memory] = local_memories
        self.local_memory_identifiers = list(owner.adjacent_nodes.keys())

        self.remote_protocol_names = []
        self.remote_memories = []

    def is_ready(self) -> bool:
        """Check if the protocol is ready to start (always ready if the distribution is not considered).

        Returns:
            bool: True if the protocol is ready, False otherwise.
        """
        return (self.remote_node_names is not None) 
    
    def start(self) -> None:
        """Start the measurement protocol."""
        log.logger.info(f"\nPROTOCOL STARTED: {self.name} starts at node {self.owner.name}")


    def set_others(self, protocols: list[str], nodes: list[str], memories: list[list[str]]) -> None:
        """Set other entanglement protocol instances for coordination.

        Args:
            protocols (list[str]): list of other protocol names.
            nodes (list[str]): list of other node names.
            memories (list[list[str]]): list of lists of memory names used on the other nodes.
        """
        self.remote_node_names = nodes
        self.remote_protocol_names = protocols
        self.remote_memories = memories
        self.received_messages = []
        self.sent_messages = []

    def perform_correction(self):
        '''Performs the correction based on the measurement outcomes received from the QLAN Orchestrator node.'''

        # Execute the quantum circuit to perform the measurements
        result = self.owner.timeline.quantum_manager.run_circuit(
                            self.circuit, 
                            [memory.qstate_key for memory in self.local_memories])

        log.logger.info(f"\nPROTOCOL ENDED: {self.owner.name} executed {self.name} at {format(self.tl.now())}")
    
    def received_message(self, src: str, message: Message):
        '''Receives the message from the QLAN Orchestrator node and performs the correction based on the measurement outcomes.
        Args:
            src (str): The source node name.
            message (Message): The received message.
        '''

        assert src in self.remote_node_names
        self.received_messages.append(message)
        log.logger.info(f"\nMESSAGE RECEIVED: {self.owner.name} received message from {src} of type {message.msg_type}  at {format(self.tl.now())}")

        n = len(self.local_memories)
        self.circuit = Circuit(n)

        if message.msg_type == QlanB0MsgType.B0_Designation:
            self.B0 = True

        elif message.msg_type == QlanMeasurementMsgType.Z_Outcome0:

            log.logger.info(f"\nAPPLYING CORRECTION: No correction is needed at {self.owner.name}")
            new_msg = Message(QlanCorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
            self.sent_messages.append(new_msg)
        
        elif message.msg_type is QlanMeasurementMsgType.Z_Outcome1:
            
            for i in range(n):
                log.logger.info(f"\nAPPLYING CORRECTION: Applying Z at {self.owner.name}")
                self.circuit.z(i)

            self.perform_correction()
            new_msg = Message(QlanCorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
            self.sent_messages.append(new_msg)
        
        elif message.msg_type is QlanMeasurementMsgType.Y_Outcome0:

            for i in range(n):
                log.logger.info(f"\nAPPLYING CORRECTION: Applying root iZ at {self.owner.name}")
                self.circuit.root_iZ(i)
            
            self.perform_correction()
            new_msg = Message(QlanCorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
            self.sent_messages.append(new_msg)
        
        elif message.msg_type is QlanMeasurementMsgType.Y_Outcome1:

            for i in range(n):
                log.logger.info(f"\nAPPLYING CORRECTION: Applying minus root iZ at {self.owner.name}")
                self.circuit.minus_root_iZ(i)

            self.perform_correction()
            new_msg = Message(QlanCorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
            self.sent_messages.append(new_msg)
        
        elif message.msg_type is QlanMeasurementMsgType.X_Outcome0:

            if self.B0 == True:
                for i in range(n):
                    log.logger.info(f"\nAPPLYING CORRECTION: Applying minus root iY at {self.owner.name}")
                    self.circuit.minus_root_iY(i)
                self.B0 = False
            else:
                for i in range(n):
                    log.logger.info(f"\nAPPLYING CORRECTION: Applying Z at {self.owner.name}")
                    self.circuit.z(i)

            self.perform_correction()
            new_msg = Message(QlanCorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
            self.sent_messages.append(new_msg)
        
        elif message.msg_type is QlanMeasurementMsgType.X_Outcome1:
            
            if self.B0 == True:
                for i in range(n):
                    log.logger.info(f"\nAPPLYING CORRECTION: Applying root iY at {self.owner.name}")
                    self.circuit.root_iY(i)
                self.B0 = False
            else:
                for i in range(n):
                    log.logger.info(f"\nAPPLYING CORRECTION: Applying Z at {self.owner.name}")
                    self.circuit.z(i)

            self.perform_correction()
            new_msg = Message(QlanCorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
            self.sent_messages.append(new_msg)
        
        else:
            raise ValueError(f"Unknown message type received: {message.msg_type}")
            
    def memory_expire(self, memory: "Memory") -> None:
        """Handle memory expiration events.

        Args:
            memory (Memory): The memory that has expired.
        """
        assert memory in self.local_memories
        # Update the resource manager about the expired memory

    def release(self) -> None:
        """Release resources used by the protocol."""
        pass