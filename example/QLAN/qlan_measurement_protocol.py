from sequence.components.circuit import Circuit
from sequence.components.memory import Memory
from sequence.topology.node import Node
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

from sequence.components.optical_channel import ClassicalChannel
from sequence.message import Message
from sequence.utils import log

from enum import Enum, auto

class MsgType(Enum):
    Outcome0 = auto()
    Outcome1 = auto()


class MeasurementProtocol(EntanglementProtocol):
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

    def __init__(self, owner: "Node", name: str, tl: "Timeline", local_memories: list[Memory], remote_memories: list[Memory], bases: str):
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
        
        # Local Memories 
        self.local_memories: list[Memory] = local_memories
        
        # TODO: uncomment this line when adjacent_nodes are instantiated after ent_generation at the orchestrator
        
        self.local_memory_identifiers = list(owner.adjacent_nodes.keys())
        #print("Local memories: ", self.local_memory_identifiers)

        self.bases: str = bases
        self.remote_node_names = remote_memories
        
        self.remote_protocol_names = []
        self.remote_memories = []
        #self.adjacent_nodes = owner.adjacent_nodes

        n = len(local_memories)  # Number of qubits (and memories)
        
        if n != len(bases):
            raise ValueError("The number of qubits at the orchestrator does not match the number of measurement bases.")
        
        # Dynamically create the quantum circuit for measurement
        self.circuit = Circuit(n)

        for i in range(n):
            base = bases[i]
            if base == "z" or base == "Z":
                self.circuit.measure(i)

            elif base == "x" or base == "X":
                self.circuit.h(i)
                self.circuit.measure(i)

            elif base == "y" or base == "Y":
                self.circuit.sdg(i)
                self.circuit.h(i)
                self.circuit.measure(i)

            else:
                raise ValueError("Invalid bases. Please use one of the supported bases: x, y, z")


    def is_ready(self) -> bool:
        """Check if the protocol is ready to start (always ready if the distribution is not considered).

        Returns:
            bool: True if the protocol is ready, False otherwise.
        """
        return True

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
    
    def start(self, owner) -> None:
        """Start the measurement protocol."""
        log.logger.info(f"{self.owner.name} protocol start at node {self.owner.name}")

        # Execute the quantum circuit to perform the measurements
        result = self.owner.timeline.quantum_manager.run_circuit(
                           self.circuit, 
                           [memory.qstate_key for memory in self.local_memories],
                           meas_samp = self.owner.get_generator().random())

        print(f"Measurement protocol executed at {self.owner.name}.")
        #print("The key of the first qubit is: ", result)

    def sendOutcomeMessages(self, tl: "Timeline"):
        # Please notice that the index is given by the order of the memories in the list declared in main
        
        #print(tl.quantum_manager.states[0].state)
        #print(tl.quantum_manager.states[1].state)
        #print(tl.quantum_manager.states[2].state)
        #print(tl.quantum_manager.states[3].state)
        #print(tl.quantum_manager.states[4].state)

        # TODO: this messages should be sent only to the adjacent qubits for each orchestrator qubit!
        print(self.local_memory_identifiers)

        for identifier in self.local_memory_identifiers:
            if (tl.quantum_manager.states[identifier].state == [1.+0.j, 0.+0.j]).any():
                for i in self.owner.adjacent_nodes[identifier]:
                    print("Outcome 0")
                    #new_msg = Message(MsgType.Outcome0, self.others_name[i])
                    #self.owner.send_message(, new_msg)

            elif tl.quantum_manager.states[4] == [0.+0.j, 1.+0.j].any():
                for i in self.owner.adjacent_nodes[identifier]:
                    print("Outcome 1")
                    #new_msg = Message(MsgType.Outcome0, self.others_name[i])
                    #self.owner.send_message(, new_msg)


    def memory_expire(self, memory: "Memory") -> None:
        """Handle memory expiration events.

        Args:
            memory (Memory): The memory that has expired.
        """
        assert memory in self.local_memories
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
