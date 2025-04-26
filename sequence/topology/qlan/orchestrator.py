from typing import List
from ..node import Node
from ...kernel.timeline import Timeline
from ...components.memory import Memory
from ...message import Message
from ...app.request_app import RequestApp
from ...qlan.measurement import QlanMeasurementProtocol
from ...qlan.graph_gen import generate_g_state


class QlanOrchestratorStateManager:
    """ 
    This class represents a state manager for the QLAN Orchestrator node.
    It provides methods to update the state of the memories and create a protocol for the owner.

    Args:
        owner (object): The owner object.
        tl (Timeline): The timeline object.
        memory_names (list): The names of the memories.
        bases (str): The set of bases.
        raw_counter (int): The counter for raw memories.
        ent_counter (int): The counter for entangled memories.
    """
    def __init__(self, owner, tl, memory_names):
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
        Sets the memories of the manager equal to the owner's memories and sets the owner's protocol to QlanMeasurementProtocol.
        """
        memory_objects = [self.owner.components[memory_name] for memory_name in self.memory_names]
        
        # Trying adaptive measurement protocol
        self.owner.protocols = [
            QlanMeasurementProtocol(owner=self.owner, name='Measurement Protocol', tl=self.tl, local_memories=memory_objects, remote_memories = self.owner.remote_memory_names, bases = self.bases),
        ]
    
    def generate_chain_state(self, tl, local_memories: List[Memory], remote_memories: List[Memory]):
        """function for linear graph state generation (abstract generation, without real distribution of states, i.e., cheating)
           TODO: May be extended with teleportation protocols
        """
        # Requires memory objects to work! (abstraction: it should be able to set only local memories)
        n = len(local_memories) + len(remote_memories)
        
        # 1/sqrt(2)|000> + 0 +...+ 0 + 1/sqrt(2)|111>
        g_state = generate_g_state(n)

        # Resetting the memories
        for memo in local_memories:
            memo.reset()
        for memo in remote_memories:
            memo.reset()
        
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

        qstate_keys = [memo.qstate_key for memo in combined_memories]
        tl.quantum_manager.set(qstate_keys, g_state)
        self.owner.find_adjacent_nodes(tl, remote_memories)


class QlanOrchestratorNode(Node):
    """
    This class represents a network node that shares a GHZ state.
    It inherits from the class "Node" and adds the memories as components and the simple manager.

    Args:
        name (str): The name of the node.
        tl (Timeline): The timeline object.
        num_local_memories (int): The number of local memories to add as components.
        remote_memories (List[Memory]): The list of remote memories to add as components. NOTE: orchestrator node should not have access to remote memory
        memo_fidelity (float): The fidelity of the memories.
        memo_frequency (int): The frequency of the memories.
        memo_efficiency (float): The efficiency of the memories.
        memo_coherence_time (float): The coherence time of the memories.
        memo_wavelength (float): The wavelength of the memories.
        bases (str): The set of bases.
    """
    
    def __init__(self, name: str, tl: Timeline, num_local_memories: int, remote_memories: List[Memory], memo_fidelity = 0.9, memo_frequency: int = 2000, memo_efficiency: float = 1, memo_coherence_time: float = -1, memo_wavelength: float = 500):
        """
        Initializes a new instance of the OrchestratorNode class.

        Args:
            name (str): The name of the node.
            tl (Timeline): The timeline object.
            local_memories (List[Memory]): The list of local memories to add as components.
            remote_memories (List[Memory]): The list of remote memories to add as components.
        """
        super().__init__(name, tl)

        self.memory_fidelity = memo_fidelity
        self.memory_frequency = memo_frequency
        self.memory_efficiency = memo_efficiency
        self.memory_coherence_time = memo_coherence_time
        self.memory_wavelength = memo_wavelength
        self.remote_memories = remote_memories
        self.remote_memory_names = [memory.name for memory in remote_memories]
        self.local_memory_names = [f'{name}.memo_o_{i}' for i in range(1, num_local_memories+1)]
        
        self.local_memories = [Memory(name=memory_name, 
                                timeline=tl, 
                                fidelity=self.memory_fidelity, 
                                frequency=self.memory_frequency,
                                efficiency=self.memory_efficiency,
                                coherence_time=self.memory_coherence_time,
                                wavelength=self.memory_wavelength) for
                                memory_name in self.local_memory_names]

        if len(self.local_memories) != len(remote_memories)-1:
            raise ValueError(f"The number of local memories {len(self.local_memories)} is invalid. It should be equal to the number of remote memories {len(remote_memories)} minus 1.")
        
        for memory in self.local_memories:
            self.add_component(memory)

        # Set the bases (default is all 'z' measurements)
        self.bases = 'z' * len(self.local_memories)
        self.resource_manager = QlanOrchestratorStateManager(owner=self, tl=tl, memory_names=self.local_memory_names)
        self.resource_manager.generate_chain_state(tl, self.local_memories, remote_memories)

    def find_adjacent_nodes(self, tl: "Timeline", remote_memories: List[Memory]):

        self.adjacent_nodes = {}
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
    
    def start_measurement(self):
        self.protocols[0].start()

    def receive_message(self, src: str, msg: "Message"):
        self.protocols[0].received_message(src, msg)

    def set_app(self, app: "RequestApp"):
        """Method to add an application to the node."""

        self.app = app

    def reset_linear_state(self, tl: "Timeline"):

        self.resource_manager.generate_chain_state(tl, self.local_memories, self.remote_memories)