from sequence.components.circuit import Circuit
from sequence.components.memory import Memory
from sequence.topology.node import Node
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

from sequence.components.optical_channel import ClassicalChannel
from sequence.message import Message
from sequence.utils import log

from .qlan_measurement_protocol import MeasurementMsgType, B0MsgType


from enum import Enum, auto

class CorrectionMsgType(Enum):
    ACK_Outcome0 = auto()
    ACK_Outcome1 = auto()

class CorrectionProtocol(EntanglementProtocol):
    """Protocol for the measurement of qubits retained at the orchestrator.

    This class provides an implementation of this protocol. 
    It should be instantiated on an orchestrator node.

    Variables:
        circuit (Circuit): Circuit that performs the measurements.

    Attributes:
        owner (Node): Node that protocol instance is attached to.
        name (str): Label for protocol instance.
        local_memories (list[Memory]): Memories at the orchestrator.
        remote_memories (list[str]): Names of memories on the client nodes.
        bases (str): Bases for the measurements (one for each qubit).
    """

    def __init__(self, owner: "Node", name: str, tl: "Timeline", local_memories: list[Memory]):
        """Initialize the local measurement protocol.

        Args:
            owner (Node): The node that owns this protocol instance.
            name (str): The name of this protocol instance.
            local_memories (list[Memory]): List of local memories at the orchestrator.
            remote_memories (list[Memory]): List of remote memories on the client nodes.
            bases (str): Bases for the measurements (one for each qubit).
        """
        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.B0 = False
        
        # Local Memories 
        self.local_memories: list[Memory] = local_memories
        
        self.local_memory_identifiers = list(owner.adjacent_nodes.keys())
        #print("Local memories: ", self.local_memory_identifiers)

        self.remote_protocol_names = []
        self.remote_memories = []
        #self.adjacent_nodes = owner.adjacent_nodes

    def is_ready(self) -> bool:
        """Check if the protocol is ready to start (always ready if the distribution is not considered).

        Returns:
            bool: True if the protocol is ready, False otherwise.
        """
        return (self.remote_node_names is not None) 
    
    def start(self) -> None:
        """Start the measurement protocol."""
        #log.logger.info(f"{self.name} protocol start at node {self.owner.name}")
        print(f"{self.name} protocol starts at node {self.owner.name}")

        # DEBUG
        # Send a message to the first remote node
        #if self.remote_node_names:
        #    print(f"Sending a message to {self.remote_node_names}")
        #    message = Message(CorrectionMsgType.ACK_Outcome0, self.owner.name)
        #    self.owner.send_message(self.remote_node_names, message)


    def set_others(self, protocols: list[str], nodes: list[str], memories: list[list[str]]) -> None:
        """Set other entanglement protocol instances for coordination.

        Args:
            protocols (List[str]): List of other protocol names.
            nodes (List[str]): List of other node names.
            memories (List[List[str]]): List of lists of memory names used on the other nodes.
        """
        self.remote_node_names = nodes
        self.remote_protocol_names = protocols
        self.remote_memories = memories

    def perform_correction(self):

        # Execute the quantum circuit to perform the measurements
        result = self.owner.timeline.quantum_manager.run_circuit(
                           self.circuit, 
                           [memory.qstate_key for memory in self.local_memories],
                           meas_samp = self.owner.get_generator().random())

        print(f"Correction protocol executed at {self.owner.name}")
        #print("The key of the first qubit is: ", result)

    
    def received_message(self, src: str, message: Message):

        assert src in self.remote_node_names
        print(f"\n*-*-*-*-*-*-*-*-* {self.owner.name} *-*-*-*-*-*-*-*-*")
        print(f"Received message from {src} of type {message.msg_type} at {self.owner.name} at {format(self.tl.now())}")

        n = len(self.local_memories)
        self.circuit = Circuit(n)

        if message.msg_type == B0MsgType.B0_Designation:
            self.B0 = True

        elif message.msg_type == MeasurementMsgType.Z_Outcome0:

            # No correction circuit is needed
            new_msg = Message(CorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
        
        elif message.msg_type is MeasurementMsgType.Z_Outcome1:
            

            for i in range(n):
                self.circuit.z(i)

            self.perform_correction()
            new_msg = Message(CorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
        
        elif message.msg_type is MeasurementMsgType.Y_Outcome0:

            for i in range(n):
                self.circuit.root_iZ(i)
            
            self.perform_correction()
            new_msg = Message(CorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
        
        elif message.msg_type is MeasurementMsgType.Y_Outcome1:

            for i in range(n):
                self.circuit.minus_root_iZ(i)

            self.perform_correction()
            new_msg = Message(CorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
        
        elif message.msg_type is MeasurementMsgType.X_Outcome0:

            if self.B0 == True:
                for i in range(n):
                    print(f"Applying minus root iY")
                    self.circuit.minus_root_iY(i)
                    #self.circuit.h(i)
                self.B0 = False
            else:
                for i in range(n):
                    print(f"Applying Z")
                    self.circuit.z(i)

            self.perform_correction()
            new_msg = Message(CorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
        
        elif message.msg_type is MeasurementMsgType.X_Outcome1:
            
            if self.B0 == True:
                for i in range(n):
                    print(f"Applying root iY")
                    self.circuit.root_iY(i)
                    #self.circuit.h(i)
                self.B0 = False
            else:
                for i in range(n):
                    print(f"Applying Z")
                    self.circuit.z(i)

            self.perform_correction()
            new_msg = Message(CorrectionMsgType.ACK_Outcome0, src)
            self.owner.send_message(self.remote_node_names, new_msg)
        
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
