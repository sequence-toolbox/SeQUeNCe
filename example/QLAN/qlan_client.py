from typing import List
from sequence.topology.node import Node
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.message import Message
from sequence.utils import log
from .qlan_correction_protocol import QlanCorrectionProtocol

class QlanClientStateManager:
    """
    This class represents a state manager for the QLAN client.
    It provides methods to update the state of the memories and create a protocol for the owner.

    Attributes:
        owner (object): The owner object.
        memory_names (list): The names of the memories.
        bases (str): The set of bases.
        raw_counter (int): The counter for the number of RAW states.
        ent_counter (int): The counter for the number of entangled states.
    """
    def __init__(self, owner, tl, memory_names, remote_memories):
        self.owner = owner
        self.tl = tl
        self.memory_names = memory_names
        self.remote_memories = remote_memories

        for i, memory_name in enumerate(self.memory_names):
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
        Sets the protocol to the QlanCorrectionProtocol (from the owner) and sets the memories of the manager equal to the owner's memories.
        """
        memory_objects = [self.owner.components[memory_name] for memory_name in self.memory_names]

        self.owner.protocols = [
            QlanCorrectionProtocol(owner=self.owner, name='Correction Protocol', tl=self.tl, local_memories=memory_objects),
        ]


class QlanClientNode(Node):
    """
    This class represents the QLAN client node.
    It inherits from the class "Node" and adds the memories as components and the QLAN client state manager.

    Attributes:
        name (str): The name of the node.
        tl (Timeline): The timeline object.
        local_memories (List[Memory]): The list of local memories to add as components.
        remote_memories (List[Memory]): The list of remote memories to add as components.
    """
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        
        # Number of local memories must be set to 1 in most of the cases
        self.num_local_memories = 1

        # TODO: Must be updated when entangled whit the orchestrator
        self.remote_memories = []   
        self.adjacent_nodes = {}    
        
        # Instantiating memories
        local_memory_names= [f'{name}.memo_c_{i}' for i in range(1, self.num_local_memories+1)]

        # TODO: check if it is necessary to keep this attribute
        self.remote_memory_names = []
        
        local_memories = [Memory(name=memory_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500) for memory_name in local_memory_names]

        # Check if the number of memories is greater than 1
        if len(local_memories) > 1:
            raise ValueError("The minimum number of memories allowed is 1.")
        
        # Adding local memories components
        for memory in local_memories:
            self.add_component(memory)

        # Adding resource manager
        self.resource_manager = QlanClientStateManager(owner=self, tl=tl, memory_names=local_memory_names, remote_memories=self.remote_memories)
        

    def update_orchestrator(self, remote_memories: List[Memory]):
        """
        Updates the orchestrator with the list of remote memories.

        Args:
            remote_memories (List[Memory]): The list of remote memories.
        """
        if len(remote_memories) <= 0:
            raise ValueError("Update the orchestrator with at least one memory.")
        self.remote_memories = remote_memories
        self.resource_manager.remote_memories = remote_memories
    
    def receive_message(self, src: str, msg: "Message"):
        """
        Receives a message from a source and processes it using the chosen protocol.

        Args:
            src (str): The source of the message.
            msg ("Message"): The message to be processed.
        """
        self.protocols[0].received_message(src, msg)
