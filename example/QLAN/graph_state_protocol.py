
from sequence.components.circuit import Circuit
from sequence.components.memory import Memory
from sequence.topology.node import Node
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

from sequence.message import Message
from sequence.utils import log

class MeasurementProtocol(EntanglementProtocol):
    """
    Dynamic generation of a GHZ state across n qubits (local).
    """

    def __init__(self, owner: "Node", name: str, memories: list["Memory"], base: str):
        """
        Initialize the dynamic local GHZ protocol.

        Args:
            owner (Node): The node that owns this protocol instance.
            name (str): The name of this protocol instance.
            memories (list[Memory]): The quantum memories.
        """
        super().__init__(owner, name)
        self.memories = memories
        self.n = len(memories)  # Number of qubits (and memories)

        # Dynamically create the quantum circuit for GHZ state generation
        self.circuit = Circuit(self.n)

        if base == "z" or base == "Z":
            for i in range(0, self.n):
                self.circuit.measure(i)

        elif base == "x" or base == "X":
            for i in range(0, self.n):
                self.circuit.h(i)
                self.circuit.measure(i)

        elif base == "y" or base == "Y":
            for i in range(0, self.n):
                self.circuit.sdg(i)
                self.circuit.h(i)
                self.circuit.measure(i)
        else:
            raise ValueError("Invalid bases. Please use one of the supported bases: x, y, z")

    def start(self):
        """
        Start the dynamic GHZ generation protocol.
        """
        log.logger.info(f"{self.owner.name} measurement protocol start at node {self.owner.name}")

        # Execute the quantum circuit to generate the GHZ state
        qstate_keys = [memory.qstate_key for memory in self.memories]
        result = self.owner.timeline.quantum_manager.run_circuit(
            self.circuit, 
            qstate_keys,
            meas_samp=self.owner.get_generator().random()
        )

        print(f"Measurement generation protocol executed at {self.owner.name}.")
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
            memories (List[str]): The list of memory names used on the other node.
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


class AdaptiveMeasurementProtocol(EntanglementProtocol):
    """
    Dynamic generation of a GHZ state across n qubits (local).
    """

    def __init__(self, owner: "Node", name: str, memories: list["Memory"], bases: str):
        """
        Initialize the dynamic local GHZ protocol.

        Args:
            owner (Node): The node that owns this protocol instance.
            name (str): The name of this protocol instance.
            memories (list[Memory]): The quantum memories.
            bases (str): The string of measurement bases.
        """
        super().__init__(owner, name)
        self.memories = memories
        self.n = len(memories)  # Number of qubits (and memories)

        # Dynamically create the quantum circuit for GHZ state generation
        self.circuit = Circuit(self.n)

        if len(bases) != self.n:
            raise ValueError("Invalid bases. The length of bases must match the length of memories.")

        for i in range(self.n):
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

    def start(self):
            """
            Start the dynamic GHZ generation protocol.
            """
            log.logger.info(f"{self.owner.name} measurement protocol start at node {self.owner.name}")

            # Execute the quantum circuit to generate the GHZ state
            qstate_keys = [memory.qstate_key for memory in self.memories]
            result = self.owner.timeline.quantum_manager.run_circuit(
                self.circuit, 
                qstate_keys,
                meas_samp=self.owner.get_generator().random()
            )

            print(f"Measurement generation protocol executed at {self.owner.name}.")
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
            memories (List[str]): The list of memory names used on the other node.
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
