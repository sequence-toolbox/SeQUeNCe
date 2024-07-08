from .qlan_measurement_protocol import MeasurementProtocol
from typing import List
from sequence.topology.node import Node
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.message import Message
from sequence.utils import log
from .qlan_measurement_protocol import MeasurementProtocol

# WIP
class OrchestratorStateManager:
    """
    This class represents a GHZ state manager that keeps track of the entangled and empty memories.
    It provides methods to update the state of the memories and create a protocol for the owner.

    Attributes:
        owner (object): The owner object.
        memory_names (list): The names of the memories.
        bases (str): The set of bases.
        raw_counter (int): The counter for the number of RAW states.
        ent_counter (int): The counter for the number of entangled states.
    """

    def __init__(self, owner, memory_names):
        """
        Initializes a new instance of the OrchestratorStateManager class.

        Args:
            owner (object): The owner object.
            memory_names (list): The names of the memories.
            bases (str): The set of bases.
        """
        self.owner = owner
        self.memory_names = memory_names
        self.bases = self.owner.bases
        for i, memory_name in enumerate(memory_names):
            setattr(self, f"memory{i+1}_name", memory_name)
        self.raw_counter = 0
        self.ent_counter = 0


    def update(self, memories: list, states: list):
        """
        Updates the number of entangled and empty memories based on the state.

        Args:
            memories (list): The list of memories.
            states (list): The list of states.
        """
        for i in range(len(memories)):
            if states[i] == 'RAW':
                self.raw_counter += 1
                memories[i].reset()
            else:
                self.ent_counter += 1

    def create_protocol(self):
        """
        Sets the memories of the manager equal to the owner's memories and sets the owner's protocol to DynamicLocalGHZprotocol.
        """
        memory_objects = [self.owner.components[memory_name] for memory_name in self.memory_names]
        
        # Trying measurement protocol
        # self.owner.protocols = [MeasurementProtocol(self.owner, 'Measurement Protocol', memory_objects, base = 'y')]

        # Trying adaptive measurement protocol
        self.owner.protocols = [
            MeasurementProtocol(owner=self.owner, name='Measurement Protocol', local_memories=memory_objects, bases = self.bases),
        ]


class OrchestratorNode(Node):
    """
    This class represents a network node that shares a GHZ state.
    It inherits from the class "Node" and adds the memories as components and the simple manager.

    Attributes:
        name (str): The name of the node.
        tl (Timeline): The timeline object.
        bases (str): The set of bases.
    """
    def __init__(self, name: str, tl: Timeline, num_local_memories: int, remote_memories: List[Memory]):
        """
        Initializes a new instance of the OrchestratorNode class.

        Args:
            name (str): The name of the node.
            tl (Timeline): The timeline object.
            local_memories (List[Memory]): The list of local memories to add as components.
            remote_memories (List[Memory]): The list of remote memories to add as components.
        """
        super().__init__(name, tl)
        
        # Instantiating memories
        local_memory_names = [f'{name}.memo_o_{i}' for i in range(1, num_local_memories+1)]
        
        local_memories = [Memory(name=memory_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500) for memory_name in local_memory_names]

        # Check if the number of memories is greater than 5
        if len(local_memories) + len(remote_memories) > 5:
            raise ValueError("The minimum number of memories allowed is 5.")
        
        # Adding local memories components
        for memory in local_memories:
            self.add_component(memory)

        # Set the bases (default is all 'z' measurements)
        self.bases = 'z' * len(local_memories)

        # Adding resource manager
        self.resource_manager = OrchestratorStateManager(owner=self, memory_names=local_memory_names)
        

    def update_bases(self, bases: str):
        """
        Updates the set of bases.

        Args:
            bases (str): The new set of bases.
        """
        # Check if the input string matches the number of local_memories
        if len(bases) != len(self.local_memories):
            raise ValueError("The number of bases should match the number of local memories.")
        self.bases = bases
        self.resource_manager.bases = bases
    
    # Function for receiving classing messages using the chosen protocol
    def start_measurement(self):
        self.protocols[0].start()

    # Function for receiving classing messages using the chosen protocol
    def receive_message(self, src: str, msg: "Message"):
        self.protocols[0].received_message(src, msg)
