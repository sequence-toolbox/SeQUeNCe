from .qlan_measurement_protocol import MeasurementProtocol
from typing import List
from sequence.topology.node import Node
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.message import Message
from sequence.utils import log
from .qlan_measurement_protocol import MeasurementProtocol
from .linear_graph_state_gen import generate_g_state

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

    def __init__(self, owner, tl, memory_names):
        """
        Initializes a new instance of the OrchestratorStateManager class.

        Args:
            owner (object): The owner object.
            memory_names (list): The names of the memories.
            bases (str): The set of bases.
        """
        self.owner = owner
        self.tl = tl
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
            MeasurementProtocol(owner=self.owner, name='Measurement Protocol', tl=self.tl, local_memories=memory_objects, remote_memories = self.owner.remote_memory_names, bases = self.bases),
        ]
    
    # TODO: function for state generation (abstract generation, without real distribution of states). May be extended with teleportation protocols
    def generate_chain_state(self, tl, local_memories: List[Memory], remote_memories: List[Memory]):
        
        # Requires memory objects to work! (abstraction: it should be able to set only local memories)
        n = len(local_memories)+len(remote_memories)
        
        # 1/sqrt(2)|000> + 0 +...+ 0 + 1/sqrt(2)|111>
        g_state = generate_g_state(n)

        # Resetting the memories
        for memo in local_memories:
            memo.reset()
        for memo in remote_memories:
            memo.reset()
        
        # DEBUG
        # for i in range(len(remote_memories)):
        #    print(remote_memories[i].qstate_key)

        #for i in range(len(local_memories)):
        #    print(local_memories[i].qstate_key)


        combined_memories = []
        min_size = min(len(remote_memories), len(local_memories))
        for i in range(min_size):
            combined_memories.append(remote_memories[i])
            combined_memories.append(local_memories[i])

        # Add remaining memories from the longer list
        if len(remote_memories) > len(local_memories):
            combined_memories.extend(remote_memories[min_size:])
        else:
            combined_memories.extend(local_memories[min_size:])

        # DEBUG
        # for memo in combined_memories:
        #    print(memo.qstate_key)

        qstate_keys = [memo.qstate_key for memo in combined_memories]

        # print(qstate_keys)
        tl.quantum_manager.set(qstate_keys, g_state)

        # Find adjacent nodes
        self.owner.find_adjacent_nodes(tl, remote_memories)


class OrchestratorNode(Node):
    """
    This class represents a network node that shares a GHZ state.
    It inherits from the class "Node" and adds the memories as components and the simple manager.

    Attributes:
        name (str): The name of the node.
        tl (Timeline): The timeline object.
        bases (str): The set of bases.
    """

    # Dictionary for adjacent nodes (aka entangled nodes) for each memory.
    
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
        
        # Remote memories infos
        self.remote_memories = remote_memories
        self.remote_memory_names = [memory.name for memory in remote_memories]

        # Instantiating memories (note that the remote memories are already instantiated in the client nodes ant thus have a name)
        self.local_memory_names = [f'{name}.memo_o_{i}' for i in range(1, num_local_memories+1)]
        
        local_memories = [Memory(name=memory_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500) for memory_name in self.local_memory_names]

        # Check if the number of memories is greater than 5
        if len(local_memories) + len(remote_memories) > 5:
            raise ValueError("The minimum number of memories allowed is 5.")
        
        # Adding local memories components
        for memory in local_memories:
            self.add_component(memory)

        # Set the bases (default is all 'z' measurements)
        self.bases = 'z' * len(local_memories)

        # Adding resource manager
        self.resource_manager = OrchestratorStateManager(owner=self, tl=tl, memory_names=self.local_memory_names)

        # Generation of a chain graph state (abstract)
        self.resource_manager.generate_chain_state(tl, local_memories, remote_memories)

    def find_adjacent_nodes(self, tl: "Timeline", remote_memories: List[Memory]):

        self.adjacent_nodes = {}
        
        # TODO: Target keys should be 3 and 4: we are supposing that client memories have smaller indices than orchestration memories. This code should be generalized for a greater number of memories.
        target_keys = list(range(len(remote_memories), len(remote_memories) + len(self.local_memory_names)))

        target_array = tl.quantum_manager.states[0].keys
        print("Target keys: ",target_keys)
        
        print("Target array: ",target_array)
        for key in target_keys:
            for i in range(len(target_array)):
                if target_array[i] == key:
                    if i > 0 and i < len(target_array) - 1:
                        self.adjacent_nodes[key] = [target_array[i-1], target_array[i+1]]
                    elif i == len(target_array) - 1:
                        self.adjacent_nodes[key] = [target_array[i-1]]
        print(self.adjacent_nodes)

    def update_bases(self, bases: str):
        """
        Updates the set of bases.

        Args:
            bases (str): The new set of bases.
        """
        # Check if the input string matches the number of local_memories
        if len(bases) != len(self.local_memory_names):
            raise ValueError("The number of bases should match the number of local memories.")
        self.bases = bases
        self.resource_manager.bases = bases
    
    # Function for receiving classing messages using the chosen protocol
    def start_measurement(self):
        self.protocols[0].start()

    # Function for receiving classing messages using the chosen protocol
    def receive_message(self, src: str, msg: "Message"):
        self.protocols[0].received_message(src, msg)
