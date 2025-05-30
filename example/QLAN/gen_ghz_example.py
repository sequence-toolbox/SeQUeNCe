
# Simple generation of a n-qubit GHZ state in a n-node network.
# - (Protocol = False -- ideal) the state is generated without distribution.
# - (Protocol = True -- circuit) the state is generated with qcircuit.

from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory

from example.qlan.local_ghz_protocol import LocalGHZprotocol

class GHZStateManager:
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

    def update(self, protocol, memories: list, states: list):
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
        Sets the memories of the manager equal to the owner's memories and sets the owner's protocol to LocalGHZprotocol.
        """
        memory_objects = [self.owner.components[memory_name] for memory_name in self.memory_names]
        self.owner.protocols = [LocalGHZprotocol(self.owner, 'DynamicLocalGHZprotocol', memory_objects)]


class GHZnode(Node):
    """
    This class represents a network node that shares a GHZ state.
    It inherits from the class "Node" and adds the memories as components and the simple manager.

    Attributes:
        name (str): The name of the node.
        tl (Timeline): The timeline object.
    """
    def __init__(self, name: str, tl: Timeline):
        """
        Initializes a new instance of the GHZnode class.

        Args:
            name (str): The name of the node.
            tl (Timeline): The timeline object.
        """
        super().__init__(name, tl)
        
        memory1_name = '%s.memo1' % name
        memory2_name = '%s.memo2' % name
        memory3_name = '%s.memo3' % name
        memory4_name = '%s.memo4' % name
        
        memo1 = Memory(name=memory1_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500)
        memo2 = Memory(name=memory2_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500)
        memo3 = Memory(name=memory3_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500)
        memo4 = Memory(name=memory4_name, timeline=tl, fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500)
        # Adding memories components
        self.add_component(memo1)
        self.add_component(memo2)
        self.add_component(memo3)
        self.add_component(memo4)
        # Adding resource manager
        self.resource_manager = GHZStateManager(owner=self,
                                                memory_names=[memory1_name, memory2_name, memory3_name, memory4_name])

def entangle_memory(tl, memories, n):
    """
    Create a GHZ state across n quantum memories.

    Args:
        tl (Timeline): The timeline object.
        memories (list[Memory]): list of memory objects.
        n (int): Number of memories.

    Returns:
        None
    """
    if len(memories) != n:
        raise ValueError("Number of memories must match n.")

    SQRT_HALF = 0.5 ** 0.5
    ghz_state = [0] * (2 ** n)
    ghz_state[0] = SQRT_HALF
    ghz_state[-1] = SQRT_HALF

    for memo in memories:
        memo.reset()

    qstate_keys = [memo.qstate_key for memo in memories]
    tl.quantum_manager.set(qstate_keys, ghz_state)


def run_experiment(tl, memo_1, memo_2, memo_3, memo_4, use_protocol):
    """
    Run the experiment with the specified timeline and memories.

    Args:
        tl (Timeline): The timeline object.
        memo_1 (Memory): The first memory object.
        memo_2 (Memory): The second memory object.
        memo_3 (Memory): The third memory object.
        memo_4 (Memory): The fourth memory object.
        use_protocol (bool): Flag indicating whether to use the protocol or not.
    """
    tl.init()

    if use_protocol:
        node1.resource_manager.create_protocol()
        node1.protocols[0].start()
    else:
        for i in range(10):
            entangle_memory(tl, [memo_1, memo_2, memo_3, memo_4], 4)

    tl.run()

def display_state_information(tl, memo_1, memo_2, memo_3, memo_4):
    """
    Display the state information of the given memories and the corresponding quantum states stored in the quantum manager.

    Args:
        tl (Timeline): The timeline object.
        memo_1 (Memory): The first memory object.
        memo_2 (Memory): The second memory object.
        memo_3 (Memory): The third memory object.
        memo_4 (Memory): The fourth memory object.
    """
    print(memo_1.name, memo_1.entangled_memory, memo_1.fidelity)
    print(memo_2.name, memo_2.entangled_memory, memo_2.fidelity)
    print(memo_3.name, memo_3.entangled_memory, memo_3.fidelity)
    print(memo_4.name, memo_4.entangled_memory, memo_4.fidelity)

    print(f"Quantum state stored in memory{memo_1.qstate_key+1}:\n {tl.quantum_manager.states[0]}")
    print(f"Quantum state stored in memory{memo_2.qstate_key+1}:\n {tl.quantum_manager.states[1]}")
    print(f"Quantum state stored in memory{memo_3.qstate_key+1}:\n {tl.quantum_manager.states[2]}")
    print(f"Quantum state stored in memory{memo_4.qstate_key+1}:\n {tl.quantum_manager.states[3]}")

# MAIN PROCESS:
# 1. Instantiate the timeline and nodes.
# 2. Create the communication channel.
# 3. Initialize quantum memories and configure settings.
# 4. Set up the resource manager for node operations.
# 5. Establish connections between nodes.
# 6. Activate protocols and begin the simulation.
if __name__ == '__main__':

    tl = Timeline()
    node1 = GHZnode('node1', tl)
    node1.set_seed(28)

    memo_1 = node1.components[node1.resource_manager.memory1_name]
    memo_2 = node1.components[node1.resource_manager.memory2_name]
    memo_3 = node1.components[node1.resource_manager.memory3_name]
    memo_4 = node1.components[node1.resource_manager.memory4_name]

    run_experiment(tl=tl, memo_1=memo_1, memo_2=memo_2, memo_3=memo_3, memo_4=memo_4, use_protocol=True)
    display_state_information(tl=tl, memo_1=memo_1, memo_2=memo_2, memo_3=memo_3, memo_4=memo_4)

