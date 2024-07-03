################################################################################
# Simple generation of a n-qubit Linear Graph state in a single node network.
# - IDEAL: the state is generated without distribution.
################################################################################

# Basic components
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory

# Log utility
import sequence.utils.log as log
from sequence.utils import log

from ..linear_graph_state_gen import *
from ..graph_state_protocol import MeasurementProtocol, AdaptiveMeasurementProtocol

class GraphStateManager:
    """
    This class represents a GHZ state manager that keeps track of the entangled and empty memories.
    It provides methods to update the state of the memories and create a protocol for the owner.

    Attributes:
        owner (object): The owner object.
        memory_names (list): The names of the memories.
        raw_counter (int): The counter for the number of RAW states.
        ent_counter (int): The counter for the number of entangled states.
    """

    def __init__(self, owner, memory_names):
        """
        Initializes a new instance of the GHZStateManager class.

        Args:
            owner (object): The owner object.
            memory_names (list): The names of the memories.
        """
        self.owner = owner
        self.memory_names = memory_names
        for i, memory_name in enumerate(memory_names):
            setattr(self, f"memory{i+1}_name", memory_name)
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, memories: list, states: list):
        """
        Updates the number of entangled and empty memories based on the state.

        Args:
            protocol: The protocol object.
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
        self.owner.protocols = [AdaptiveMeasurementProtocol(self.owner, 'Measurement Protocol', memory_objects, bases = 'yyzzz')]

################################################################################
# GraphStateNode: network node that shares a GHZ state. It inherits from the class "Node" then adds the memories as components and the simple manager.
# In this case, we suppose that the Graph state node has 5 memories
################################################################################

class GraphStateNode(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)
        
        # Instantiating memories
        memory_names = [f'{name}.memo{i}' for i in range(1, 6)]  # Updated to include 5 memories
        
        memories = [Memory(name=memory_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500) for memory_name in memory_names]
        
        # Adding memories components
        for memo in memories:
            self.add_component(memo)
        
        # Adding resource manager
        self.resource_manager = GraphStateManager(owner=self, memory_names=memory_names)

def run_experiment(tl, memo_1, memo_2, memo_3, memo_4, memo_5):
    tl.init()
        
    for i in range(10):
        entangle_memory(tl, [memo_1, memo_2, memo_3, memo_4, memo_5], 5)  # Updated to include memo_5

    tl.run()

def display_state_information(tl, memo_1, memo_2, memo_3, memo_4, memo_5):
    
    # Print the name, entangled memory, and fidelity of each memory
    print(memo_1.name, memo_1.entangled_memory, memo_1.fidelity)
    print(memo_2.name, memo_2.entangled_memory, memo_2.fidelity)
    print(memo_3.name, memo_3.entangled_memory, memo_3.fidelity)
    print(memo_4.name, memo_4.entangled_memory, memo_4.fidelity)
    print(memo_5.name, memo_5.entangled_memory, memo_5.fidelity)  
    
    # Print the quantum state stored in each memory
    print(f"Quantum state stored in memory{memo_1.qstate_key+1}:\n {tl.quantum_manager.states[0]}")
    print(f"Quantum state stored in memory{memo_2.qstate_key+1}:\n {tl.quantum_manager.states[1]}")
    print(f"Quantum state stored in memory{memo_3.qstate_key+1}:\n {tl.quantum_manager.states[2]}")
    print(f"Quantum state stored in memory{memo_4.qstate_key+1}:\n {tl.quantum_manager.states[3]}")
    print(f"Quantum state stored in memory{memo_5.qstate_key+1}:\n {tl.quantum_manager.states[4]}") 

if __name__ == '__main__':
    # Create a timeline
    tl = Timeline()

    # Create a GraphStateNode
    node1 = GraphStateNode('node1', tl)
    node1.set_seed(28)

    # Get the memories from the node
    memo_1 = node1.components[node1.resource_manager.memory1_name]
    memo_2 = node1.components[node1.resource_manager.memory2_name]
    memo_3 = node1.components[node1.resource_manager.memory3_name]
    memo_4 = node1.components[node1.resource_manager.memory4_name]
    memo_5 = node1.components[node1.resource_manager.memory5_name]  # Added memo_5

    # Run the experiment with the given memories
    run_experiment(tl=tl, memo_1=memo_1, memo_2=memo_2, memo_3=memo_3, memo_4=memo_4, memo_5=memo_5)

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, memo_1=memo_1, memo_2=memo_2, memo_3=memo_3, memo_4=memo_4, memo_5=memo_5)

    # Measurement Protocol Test
    node1.resource_manager.create_protocol()
    node1.protocols[0].start()

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, memo_1=memo_1, memo_2=memo_2, memo_3=memo_3, memo_4=memo_4, memo_5=memo_5)

