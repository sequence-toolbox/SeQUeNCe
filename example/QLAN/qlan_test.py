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


# TODO: Class for managing experiments. Should be able to instatiate nodes, run experiments and display results with the topology expressed with json files.
def pair_protocol(orchestrator: OrchestratorNode, clients: List[ClientNode]):
    
    # WIP: associate memories correctly, modify set_others if needed
    p_orch = orchestrator.protocols[0]
    orch_memo_name1 = orchestrator.resource_manager.memory_names[0]
    orch_memo_name2 = orchestrator.resource_manager.memory_names[1]
    protocols_names = []
    clients_names = []
    clients_memory_names = []
    
    for client in clients:
        p_client = client.protocols[0]
        protocols_names.append(p_client)
        clients_names.append(client.name)
        clients_memory_names.append(client.resource_manager.memory_names[0])

        p_client.set_others(p_orch.name, orchestrator.name, [orch_memo_name1, orch_memo_name2])

    p_orch.set_others(protocols_names, clients_names, [orch_memo_name1, orch_memo_name2])

def run_experiment(tl, local_memories, remote_memories):
    tl.init()
    
    # TODO: Generation Moved to the OrchestratorStateManager. This may be extended to distribution process!
    #for i in range(10):
    #    qlan_entangle_memory(tl=tl, local_memories=local_memories, remote_memories=remote_memories, n=5)

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
    
    # Getting remote memory names
    memo_c_1_name = client1.components[client1.resource_manager.memory1_name]
    memo_c_2_name = client2.components[client2.resource_manager.memory1_name]
    memo_c_3_name = client3.components[client3.resource_manager.memory1_name]

    # Getting remote memory components
    memo_c_1 = client1.get_components_by_type("Memory")[0]
    memo_c_2 = client2.get_components_by_type("Memory")[0]
    memo_c_3 = client3.get_components_by_type("Memory")[0]

    # Create Orchestrator node and clients
    orch = OrchestratorNode('Orchestrator', tl, num_local_memories=2, remote_memories=[memo_c_1, memo_c_2, memo_c_3])
    
    # Seed to obtain 0s as results measurements at the orchestrator
    orch.set_seed(2332)

    # Get the memories from the node
    memo_o_1 = orch.components[orch.resource_manager.memory1_name]
    memo_o_2 = orch.components[orch.resource_manager.memory2_name]

    orch.update_bases('yy')

    orch.resource_manager.create_protocol()
    client1.resource_manager.create_protocol()
    client2.resource_manager.create_protocol()
    client3.resource_manager.create_protocol()

    pair_protocol(orchestrator=orch, clients=[client1, client2, client3])

    # Run the experiment with the given memories
    run_experiment(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

    print("\n ----  Orchestrator Measurement ---- \n")

    orch.protocols[0].start(orch)
    orch.protocols[0].sendOutcomeMessages(tl)

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

