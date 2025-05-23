from collections import defaultdict
from ..components.circuit import Circuit
from ..components.memory import Memory
from ..topology.node import Node
from ..entanglement_management.entanglement_protocol import EntanglementProtocol
from ..kernel.timeline import Timeline
from ..message import Message
from ..utils import log

from enum import Enum, auto

class QlanMeasurementMsgType(Enum):
    """Measurement outcomes at the orchestrator
    """
    Z_Outcome0 = auto()
    Z_Outcome1 = auto()
    Y_Outcome0 = auto()
    Y_Outcome1 = auto()
    X_Outcome0 = auto()
    X_Outcome1 = auto()

class QlanB0MsgType(Enum):
    B0_Designation = auto()

class QlanMeasurementProtocol(EntanglementProtocol):
    """Protocol for the measurement of qubits retained at the orchestrator.

    This class provides an implementation of the measurement protocol for qubits that are retained at the orchestrator. 
    It should be instantiated on an orchestrator node.

    Variables:
        circuit (Circuit): Circuit that performs the measurements.

    Attributes:
        owner (Node): Node that the protocol instance is attached to.
        name (str): Label for the protocol instance.
        tl (Timeline): The timeline object for tracking the progress of the protocol.
        local_memories (list[Memory]): Memories at the orchestrator.
        remote_memories (list[str]): Names of memories on the client nodes.
        bases (str): Bases for the measurements (one for each qubit).
        sent_messages (list): list of sent messages.
        remote_node_names (list[str]): Names of the remote nodes.
        remote_protocol_names (list[str]): Names of the remote protocols.
        message_list (defaultdict): Dictionary to store the outcome messages.
    """

    def __init__(self, owner: "Node", name: str, tl: "Timeline", local_memories: list[Memory], remote_memories: list[Memory], bases: str):

        super().__init__(owner, name)
        self.owner = owner
        self.name = name
        self.tl = tl
        self.local_memories: list[Memory] = local_memories
        self.local_memory_identifiers = list(owner.adjacent_nodes.keys())
        self.bases: str = bases
        self.sent_messages = []

        # N_a u N_{\hat a}
        self.remote_node_names = remote_memories    
        
        self.remote_protocol_names = []
        self.remote_memories = []

        n = len(local_memories)
        
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
        """Check if the protocol is ready to start.

        Returns:
            bool: True if the protocol is ready, False otherwise.
        """
        return (self.remote_node_names is not None) 

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
        self.message_list = defaultdict(list)
    
    def start(self, tl) -> None:
        """Start the measurement protocol.

        Args:
            tl (Timeline): The timeline object for tracking the progress of the protocol.
        """
        log.logger.info(f"\nPROTOCOL STARTED: {self.name} starts at node {self.owner.name}")

        result = self.owner.timeline.quantum_manager.run_circuit(
                            self.circuit, 
                            [memory.qstate_key for memory in self.local_memories],
                            meas_samp = self.owner.get_generator().random())
        self.send_outcome_messages(self.tl)

    def send_outcome_messages(self, tl: "Timeline"):
        '''Send the outcomes of the measurements to the clients, based on the measurement outcomes and chosen bases.

        Args:
            tl (Timeline): The timeline object.

        Returns:
            None
        '''

        log.logger.debug(f"\nORCHESTRATOR DEBUG: init message_list {self.message_list}")
        log.logger.debug(f"\nORCHESTRATOR DEBUG: adjacent_nodes {self.owner.adjacent_nodes}")
        log.logger.debug(f"\nORCHESTRATOR DEBUG: local_memory_identifiers {self.local_memory_identifiers}")

        base_count = 0
        for identifier in self.local_memory_identifiers:

            log.logger.debug(f"\nORCHESTRATOR DEBUG: CURRENT IDENTIFIER {identifier}")

            # Case Outcome "0"
            if (tl.quantum_manager.states[identifier].state == [1.+0.j, 0.+0.j]).any():
                
                Na = self.owner.adjacent_nodes[identifier]
                Nb0 = []
                dest_sample = []
                b0 = None

                log.logger.debug(f"\nORCHESTRATOR DEBUG: Na is now updated {Na}")
                
                # Case of Measurement in the Z basis
                if self.bases[base_count] == "z" or self.bases[base_count] == "Z":
                    msg_type = QlanMeasurementMsgType.Z_Outcome0
                    dest_sample = Na
                    
                    for dest in dest_sample:
                        if dest in self.message_list:
                            self.message_list[dest].append(msg_type)
                        else:
                            self.message_list[dest] = [msg_type]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: message_list {self.message_list}")

                # Case of Measurement in the Y basis
                elif self.bases[base_count] == "y" or self.bases[base_count] == "Y":
                    msg_type = QlanMeasurementMsgType.Y_Outcome0
                    dest_sample = Na
                    
                    for dest in dest_sample:
                        if dest in self.message_list:
                            self.message_list[dest].append(msg_type)
                        else:
                            self.message_list[dest] = [msg_type]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: message_list {self.message_list}")
                    
                # Case of Measurement in the X basis
                elif self.bases[base_count] == "x" or self.bases[base_count] == "X":
                    msg_type = QlanMeasurementMsgType.X_Outcome0
                    b0 = Na[1]
                    # Sending "b_0" message to the chosen node (first available node in the adjacency list -- choice is arbitary):
                    
                    log.logger.info(f"\nORCHESTRATOR: Selected b0 = {b0} from {self.owner.adjacent_nodes}")
                    
                    Nb0 = [key for key, value in self.owner.adjacent_nodes.items() if b0 in value]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: Nb0 is now updated {Nb0}")
                    
                    new_msg = Message(QlanB0MsgType.B0_Designation, self.remote_node_names[b0])

                    log.logger.info(f"\nORCHESTRATOR: Sending: {new_msg.msg_type} to {self.remote_node_names[b0]} at {format(self.tl.now())}")

                    self.owner.send_message(self.remote_node_names[b0], new_msg)
                        
                    # Sending the outcomes to {b0} u {N_a \ (N_b0 u {b0})}
                    dest_sample = [node for node in Na if node not in Nb0 and node != b0]
                    dest_sample.append(b0)
                    
                    for dest in dest_sample:
                        if dest in self.message_list:
                            self.message_list[dest].append(msg_type)
                        else:
                            self.message_list[dest] = [msg_type]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: message_list {self.message_list}")

                # Unknown measurement basis
                else:
                    raise ValueError("Invalid bases. Please use one of the supported bases: x, y, z")
                        
            # Case Outcome "1"
            if (tl.quantum_manager.states[identifier].state == [0.+0.j, 1.+0.j]).any():
                
                Na = self.owner.adjacent_nodes[identifier]
                Nb0 = []
                dest_sample = []
                b0 = None

                log.logger.debug(f"\nORCHESTRATOR DEBUG: Na is now updated {Na}")
                    
                # Case of Measurement in the Z basis
                if self.bases[base_count] == "z" or self.bases[base_count] == "Z":
                    msg_type = QlanMeasurementMsgType.Z_Outcome1
                    dest_sample = Na

                    for dest in dest_sample:
                        if dest in self.message_list:
                            self.message_list[dest].append(msg_type)
                        else:
                            self.message_list[dest] = [msg_type]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: message_list {self.message_list}")
                    
                # Case of Measurement in the X basis
                elif self.bases[base_count] == "y" or self.bases[base_count] == "Y":
                    msg_type = QlanMeasurementMsgType.Y_Outcome1
                    dest_sample = Na
                    
                    for dest in dest_sample:
                        if dest in self.message_list:
                            self.message_list[dest].append(msg_type)
                        else:
                            self.message_list[dest] = [msg_type]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: message_list {self.message_list}")

                # Case of Measurement in the X basis
                elif self.bases[base_count] == "x" or self.bases[base_count] == "X":
                    msg_type = QlanMeasurementMsgType.X_Outcome1
                    b0 = Na[1]
                    # Sending "b_0" message to che chosen node (first available node in the adjacency list -- choice is arbitary):
                    #if b0 == i:
                    log.logger.info(f"\nB0 ELECTION: Selected b0 = {b0} from {self.owner.adjacent_nodes}")

                    Nb0 = [key for key, value in self.owner.adjacent_nodes.items() if b0 in value]
                    
                    log.logger.debug(f"\nORCHESTRATOR DEBUG: Nb0 is now updated {Nb0}")
                    
                    new_msg = Message(QlanB0MsgType.B0_Designation, self.remote_node_names[b0])
                    
                    log.logger.info(f"\nORCHESTRATOR: Sending: {new_msg.msg_type} to {self.remote_node_names[b0]} at {format(self.tl.now())}")
                    
                    self.owner.send_message(self.remote_node_names[b0], new_msg)
                        
                    # Sending the outcomes to {b0} u {N_a \ (N_b0 u {b0})}
                    dest_sample = [node for node in Nb0 if node not in Na and node != self.local_memory_identifiers[base_count]]
                    dest_sample.append(b0)

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: dest_sample {dest_sample}")
                    
                    for dest in dest_sample:
                        if dest in self.message_list:
                            self.message_list[dest].append(msg_type)
                        else:
                            self.message_list[dest] = [msg_type]

                    log.logger.debug(f"\nORCHESTRATOR DEBUG: message_list {self.message_list}")
                    
                # Unknown measurement basis
                else:
                    raise ValueError("Invalid bases. Please use one of the supported bases: x, y, z")
                
            self.update_adjacent_nodes(self.local_memory_identifiers[base_count], b0)                    
            base_count +=1

        # Sending the messages outcomes
        for dest, msg_type in self.message_list.items():
            # Fixing corrections at orchestrator
            if int(dest) >= len(self.remote_node_names):
                dest = dest % len(self.remote_node_names) + 1
            for i in range(0,len(self.message_list[dest])):
                new_msg = Message(msg_type[i], self.remote_node_names[dest])
                
                log.logger.info(f"\nMESSAGE SENT: {self.owner.name} is sending: {new_msg.msg_type} to {self.remote_node_names[dest]} at {format(self.tl.now())}")

                self.owner.send_message(self.remote_node_names[dest], new_msg)
                self.sent_messages.append(new_msg.msg_type)

        # reset message list after sending all messages
        self.message_list = {}

    def update_adjacent_nodes(self, current_key, b0 = None):
        '''Update the adjacent nodes of the orchestrator after the measurement outcomes are sent.
        
        Args:
            current_key: The key of the current memory.
            b0: The designated node for outcome "1" in the X basis measurement.

        Returns:
            None
        '''
        saved_values = []
        keys_to_clear = []

        if b0 is not None:
            # Check if b0 is among the values and save non-b0 values
            for key, values in self.owner.adjacent_nodes.items():
                if b0 in values:
                    saved_values.extend([val for val in values if val != b0])
                    keys_to_clear.append(key)
            
            # Replace b0 with saved_values in other keys
            for key, values in self.owner.adjacent_nodes.items():
                if b0 in values:
                    new_values = [val if val != b0 else saved_values for val in values]
                    new_values = [item for sublist in new_values for item in (sublist if isinstance(sublist, list) else [sublist])]
                    seen = set()
                    self.owner.adjacent_nodes[key] = [x for x in new_values if not (x in seen or seen.add(x))]

        self.owner.adjacent_nodes[current_key] = []

        log.logger.debug(f"\nORCHESTRATOR DEBUG: updated adjacent nodes: {self.owner.adjacent_nodes}")
        
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
        log.logger.info(f"\nMESSAGE RECEIVED: {self.owner.name} received ACK message from {src} at {format(self.tl.now())}")

    def release(self) -> None:
        """Release resources used by the protocol."""
        pass
