from typing import List
from sequence.topology.node import Node
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.message import Message
from sequence.utils import log

# Qlan imports
from .qlan_orchestrator import OrchestratorNode
from .linear_graph_state_gen import qlan_entangle_memory
from .qlan_client import ClientNode


def run_experiment(tl, local_memories, remote_memories):
    tl.init()
        
    for i in range(10):
        qlan_entangle_memory(tl=tl, local_memories=local_memories, remote_memories=remote_memories, n=5)

    tl.run()

def display_state_information(tl, local_memories, remote_memories):
    
    for i, memory in enumerate(local_memories):
        print(memory.name, memory.entangled_memory, memory.fidelity)
        print(f"Quantum state stored in memory{memory.qstate_key+1}:\n {tl.quantum_manager.states[i]}")
    
    for i, memory in enumerate(remote_memories):
        print(memory.name, memory.entangled_memory, memory.fidelity)
        print(f"Quantum state stored in memory{memory.qstate_key+1}:\n {tl.quantum_manager.states[i+len(local_memories)]}")


if __name__ == '__main__':
    # Create a timeline
    tl = Timeline()

    # Create clients (change to client objects)
    client1 = ClientNode('client1', tl)
    client2 = ClientNode('client2', tl)
    client3 = ClientNode('client3', tl)
    client1.set_seed(224)
    client2.set_seed(225)
    client3.set_seed(226)
        
    memo_c_1 = client1.components[client1.resource_manager.memory1_name]
    memo_c_2 = client2.components[client2.resource_manager.memory1_name]
    memo_c_3 = client3.components[client3.resource_manager.memory1_name]

    # Create Orchestrator node and clients
    orch = OrchestratorNode('Orchestrator', tl, num_local_memories=2,remote_memories=[memo_c_1, memo_c_2, memo_c_3])
    
    # Seed to obtain 0s as results measurements at the orchestrator
    orch.set_seed(2332)

    # Get the memories from the node
    memo_o_1 = orch.components[orch.resource_manager.memory1_name]
    memo_o_2 = orch.components[orch.resource_manager.memory2_name]

    orch.update_bases('ZZ')

    # Run the experiment with the given memories
    run_experiment(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

    print("\n ----  Orchestrator Measurement ---- \n")

    # Measurement Protocol Test
    orch.resource_manager.create_protocol()
    orch.protocols[0].start()

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

