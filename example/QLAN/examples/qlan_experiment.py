from typing import List
from sequence.topology.node import Node
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.message import Message
from sequence.utils import log
from sequence.components.optical_channel import ClassicalChannel

# Qlan imports
# Relative imports if fixed...
from ..qlan_orchestrator import OrchestratorNode
from ..linear_graph_state_gen import qlan_entangle_memory
from ..qlan_client import ClientNode
import random

'''
This benchmark file is WIP. 
It is intended to be a more user-friendly way to run experiments with QLAN.
'''

class ExperimentManager:
    def __init__(self, tl, num_clients: int, num_orch_memories: int, desired_outcomes: str, measurement_bases: str):
        self.num_clients = num_clients
        self.num_orch_memories = num_orch_memories
        self.timeline = tl
        self.desired_outcomes = desired_outcomes
        self.measurement_bases = measurement_bases
        self.orchestrator = None
        self.clients = []

        self.local_memories = []
        self.local_memories_names = []
        self.remote_memories = []
        self.remote_memories_names = []

    def setup_experiment(self):

        for i in range(self.num_clients):

            # Client Instantiation
            client = ClientNode(f"client{i+1}", self.timeline)
            client.set_seed(224 + i)
            self.clients.append(client)

            name = f"memory{1}_name"
            memo_c_name = client.components[client.resource_manager.__dict__[name]]
            memo_c = client.get_components_by_type("Memory")[0]
            
            self.remote_memories_names.append(memo_c_name)
            self.remote_memories.append(memo_c)
            self.clients.append(client)

        # Orchestrator Instantiation
        self.orchestrator = OrchestratorNode("Orchestrator", self.timeline, num_local_memories=self.num_orch_memories, remote_memories=self.remote_memories)

        if self.desired_outcomes == '000':
            self.orchestrator.set_seed(3)
        else:
            self.orchestrator.set_seed(random.randint(0, 1000))

        self.orchestrator.update_bases(self.measurement_bases)
        
        for i in range(self.num_orch_memories):
            
            memo_o = self.orchestrator.components[self.orchestrator.resource_manager.__dict__[f"memory{i+1}_name"]]
            self.local_memories_names.append(memo_o)
        
        # Channels Instantiation
        for client in self.clients:
            print(f"Creating channels between {client} and {self.orchestrator}")
            channel_to_orch = ClassicalChannel(f"C_{client}_{self.orchestrator}", self.timeline, 10, 1e9)
            channel_to_orch.set_ends(self.orchestrator, client.name)

            channel_to_client = ClassicalChannel(f"C_{self.orchestrator.name}_{client.name}", self.timeline, 10, 1e9)
            channel_to_client.set_ends(client, self.orchestrator.name)
        
        self.timeline.init()

    def run_experiment(self):
        self.pair_protocol()

        for client in self.clients:
            client.protocols[0].start()
        self.orchestrator.protocols[0].start(self.orchestrator)

        self.timeline.run()

    def pair_protocol(self):
        p_orch = self.orchestrator.protocols[0]
        orch_memo_name1 = self.orchestrator.resource_manager.memory_names[0]
        orch_memo_name2 = self.orchestrator.resource_manager.memory_names[1]
        protocols_names = []
        clients_names = []
        clients_memory_names = []
        
        for client in self.clients:
            p_client = client.protocols[0]
            protocols_names.append(p_client)
            clients_names.append(client.name)
            clients_memory_names.append(client.resource_manager.memory_names[0])

            p_client.set_others(p_orch.name, self.orchestrator.name, [orch_memo_name1, orch_memo_name2])

        p_orch.set_others(protocols_names, clients_names, [orch_memo_name1, orch_memo_name2])

    def display_state_information(self):
        print("Local Memories:")
        print("----------------------------------------")
        for i, memory in enumerate(self.local_memories):
            print(f"Memory {memory.name}:")
            print(f"  Entangled Memory: {memory.entangled_memory}")
            print(f"  Quantum state stored in memory{memory.qstate_key+1}:")
            print(f"  {tl.quantum_manager.states[i+len(local_memories)+1]}")
            print("----------------------------------------")
        
        print("Remote Memories:")
        print("----------------------------------------")
        for i, memory in enumerate(self.remote_memories):
            print(f"Memory {memory.name}:")
            print(f"  Entangled Memory: {memory.entangled_memory}")
            print(f"  Quantum state stored in memory{memory.qstate_key+1}:")
            print(f"  {tl.quantum_manager.states[i]}")
            print("----------------------------------------")

if __name__ == "__main__":

    # SIMULATION PARAMETERS HERE
    NUM_CLIENTS = 4
    NUM_ORCH_MEMORIES = 3
    DESIRED_OUTCOMES = '000'
    MEASUREMENT_BASES = 'yyy'
    

    tl = Timeline()
    
    
    experiment_manager = ExperimentManager(tl, NUM_CLIENTS, NUM_ORCH_MEMORIES, DESIRED_OUTCOMES, MEASUREMENT_BASES)
    experiment_manager.setup_experiment()
    experiment_manager.run_experiment()
    experiment_manager.display_state_information()