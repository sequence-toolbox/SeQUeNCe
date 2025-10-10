from sequence.components.circuit import Circuit
from sequence.components.memory import Memory
from sequence.topology.node import Node
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.message import Message
from sequence.utils import log

class LocalGHZ3protocol(EntanglementProtocol):
    """Generation of a 3-qubit GHZ state (local).

    This class provides an implementation of a local GHZ generation protocol.
    It should be instantiated on an orchestrator node.

    Variables:
        circuit (Circuit): Circuit that generates the 3-qubit GHZ state.

    Attributes:
        owner (Node): Node that protocol instance is attached to.
        name (str): Label for protocol instance.
        memory1 (Memory): Memory to store qubit 1.
        memory2 (Memory): Memory to store qubit 2.
        memory3 (Memory): Memory to store qubit 3.
    """

    circuit = Circuit(3)
    circuit.h(0)        
    circuit.cx(0, 1)    
    circuit.cx(0, 2)    

    def __init__(self, owner: "Node", name: str, memory1: "Memory", memory2: "Memory", memory3: "Memory"):
        """Initialize the local GHZ protocol.

        Args:
            owner (Node): The node that owns this protocol instance.
            name (str): The name of this protocol instance.
            memory1 (Memory): The first quantum memory.
            memory2 (Memory): The second quantum memory.
            memory3 (Memory): The third quantum memory.
        """
        self.owner = owner
        self.name = name
        self.memory1: Memory = memory1
        self.memory2: Memory = memory2
        self.memory3: Memory = memory3

    def is_ready(self) -> bool:
        """Check if the protocol is ready to start.

        Returns:
            bool: True if the protocol is ready, False otherwise.
        """
        return True

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Set other entanglement protocol instances for coordination.

        Args:
            protocol (str): Other protocol name.
            node (str): Other node name.
            memories (list[str]): The list of memory names used on the other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol
        self.remote_memories = memories
    
    def start(self) -> None:
        """Start the 3-qubit GHZ generation protocol."""
        log.logger.info(f"{self.owner.name} protocol start at node {self.owner.name}")

        result = self.owner.timeline.quantum_manager.run_circuit(
                            self.circuit, 
                            [self.memory1.qstate_key,
                            self.memory2.qstate_key,
                            self.memory3.qstate_key],
                            meas_samp = self.owner.get_generator().random())

        print(f"GHZ generation protocol executed at {self.owner.name}.")
        print("The key of the first qubit is: ", result)

    def memory_expire(self, memory: "Memory") -> None:
        """Handle memory expiration events.

        Args:
            memory (Memory): The memory that has expired.
        """
        assert memory in [self.memory1, self.memory2, self.memory3]
        # Update the resource manager about the expired memory

    def received_message(self, src: str, msg: Message):
        """Handle received messages.

        Args:
            src (str): The source of the message.
            msg (Message): The received message.
        """
        pass

    def release(self) -> None:
        """Release resources used by the protocol."""
        pass

class LocalGHZprotocol(EntanglementProtocol):
    """
    Dynamic generation of a GHZ state across n qubits (local).
    """

    def __init__(self, owner: "Node", name: str, memories: list["Memory"]):
        """
        Initialize the dynamic local GHZ protocol.

        Args:
            owner (Node): The node that owns this protocol instance.
            name (str): The name of this protocol instance.
            memories (list[Memory]): The quantum memories.
        """
        super().__init__(owner, name)
        self.memories = memories
        self.n = len(memories)  

        self.circuit = Circuit(self.n)
        self.circuit.h(0)  
        for i in range(1, self.n):
            self.circuit.cx(0, i)  

    def start(self):
        """
        Start the dynamic GHZ generation protocol.
        """
        log.logger.info(f"{self.owner.name} protocol start at node {self.owner.name}")

        qstate_keys = [memory.qstate_key for memory in self.memories]
        result = self.owner.timeline.quantum_manager.run_circuit(
            self.circuit, 
            qstate_keys,
            meas_samp=self.owner.get_generator().random()
        )

        print(f"GHZ generation protocol executed at {self.owner.name}.")
        print("The key of the first qubit is: ", result)

    def is_ready(self) -> bool:
        """Check if the protocol is ready to start.

        Returns:
            bool: True if the protocol is ready, False otherwise.
        """
        return True

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Set other entanglement protocol instances for coordination.

        Args:
            protocol (str): Other protocol name.
            node (str): Other node name.
            memories (list[str]): The list of memory names used on the other node.
        """
        self.remote_node_name = node
        self.remote_protocol_name = protocol
        self.remote_memories = memories

    def memory_expire(self, memory: "Memory") -> None:
        """Handle memory expiration events.

        Args:
            memory (Memory): The memory that has expired.
        """
        assert memory in self.memories
        # Update the resource manager about the expired memory

    def received_message(self, src: str, msg: Message):
        """Handle received messages.

        Args:
            src (str): The source of the message.
            msg (Message): The received message.
        """
        pass

    def release(self) -> None:
        """Release resources used by the protocol."""
        pass