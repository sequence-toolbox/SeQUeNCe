from typing import List
from sequence.topology.node import Node
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.message import Message
from sequence.utils import log
from sequence.components.optical_channel import ClassicalChannel

# Qlan imports
from ..qlan_orchestrator import OrchestratorNode
from ..linear_graph_state_gen import qlan_entangle_memory
from ..qlan_client import ClientNode

DESIRED_OUTCOMES = '11'

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

def display_state_information(tl, local_memories, remote_memories):
    print("Local Memories:")
    print("----------------------------------------")
    for i, memory in enumerate(local_memories):
        print(f"Memory {memory.name}:")
        print(f"  Entangled Memory: {memory.entangled_memory}")
        print(f"  Quantum state stored in memory{memory.qstate_key+1}:")
        print(f"  {tl.quantum_manager.states[i+len(local_memories)+1]}")
        print("----------------------------------------")
    
    print("Remote Memories:")
    print("----------------------------------------")
    for i, memory in enumerate(remote_memories):
        print(f"Memory {memory.name}:")
        print(f"  Entangled Memory: {memory.entangled_memory}")
        print(f"  Quantum state stored in memory{memory.qstate_key+1}:")
        print(f"  {tl.quantum_manager.states[i]}")
        print("----------------------------------------")


if __name__ == '__main__':
    # Create a timeline
    tl = Timeline()

    #tl = Timeline(1e12)
    tl.show_progress = False

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
    
    # Seed to obtain desired results of the measurements at the orchestrator
    if DESIRED_OUTCOMES == '00':
        orch.set_seed(3)
    elif DESIRED_OUTCOMES == '01':
        orch.set_seed(2)
    elif DESIRED_OUTCOMES == '10':
        orch.set_seed(0)
    elif DESIRED_OUTCOMES == '11':
        orch.set_seed(4)

    # Get the memories from the node
    memo_o_1 = orch.components[orch.resource_manager.memory1_name]
    memo_o_2 = orch.components[orch.resource_manager.memory2_name]
    orch.update_bases('yy')

    # Building the physical topology
    cc_o_c1 = ClassicalChannel("cc_o_c1", tl, 10, 1e9)
    cc_o_c2 = ClassicalChannel("cc_o_c2", tl, 10, 1e9)
    cc_o_c3 = ClassicalChannel("cc_o_c3", tl, 10, 1e9)
    cc_o_c1.set_ends(orch, client1.name)
    cc_o_c2.set_ends(orch, client2.name)
    cc_o_c3.set_ends(orch, client3.name)

    cc_c1_o = ClassicalChannel("cc_c1_o", tl, 10, 1e9)
    cc_c2_o = ClassicalChannel("cc_c2_o", tl, 10, 1e9)
    cc_c3_o = ClassicalChannel("cc_c3_o", tl, 10, 1e9)
    cc_c1_o.set_ends(client1, orch.name)
    cc_c2_o.set_ends(client2, orch.name)
    cc_c3_o.set_ends(client3, orch.name)

    orch.resource_manager.create_protocol()
    client1.resource_manager.create_protocol()
    client2.resource_manager.create_protocol()
    client3.resource_manager.create_protocol()
    
    tl.init()

    pair_protocol(orchestrator=orch, clients=[client1, client2, client3])

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

    print("\n ----  Orchestrator Measurement ---- \n")

    client1.protocols[0].start()
    client2.protocols[0].start()
    client3.protocols[0].start()
    orch.protocols[0].start(orch)

    tl.run()

    # Display the state information (stored in the State Manager!)
    display_state_information(tl=tl, local_memories=[memo_o_1, memo_o_2], remote_memories=[memo_c_1, memo_c_2, memo_c_3])

