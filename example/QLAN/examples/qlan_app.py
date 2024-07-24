from typing import List

from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.qlan_star_topo import QlanStarTopo
from sequence.resource_management.memory_manager import MemoryInfo
from sequence.network_management.reservation import Reservation
from sequence.kernel.timeline import Timeline
import sequence.utils.log as log

# Qlan imports
from sequence.qlan.qlan_orchestrator import QlanOrchestratorNode
from sequence.qlan.graph_gen import qlan_entangle_memory
from sequence.qlan.qlan_client import QlanClientNode

'''
This benchmark file is WIP. 
It is intended to be a more user-friendly way to run experiments with QLAN.
'''

class PeriodicApp:
    def __init__(self, tl: "Timeline", orchestrator: "QlanOrchestratorNode", clients: List["QlanClientNode"]):
        self.orch = orchestrator
        self.orch.set_app(self)
        self.clients = clients
        self.tl = tl

        self.local_memories = []
        for i in range(len(self.orch.resource_manager.memory_names)):
            memo = self.orch.components[self.orch.resource_manager.memory_names[i]]
            self.local_memories.append(memo)

        self.remote_memories = []
        for node_obj in clients:
            memo = node_obj.get_components_by_type("Memory")[0]
            self.remote_memories.append(memo)

        self.pair_protocol()
        self.display_state_information()

    def start(self):
        now = self.orch.timeline.now()
                
        # schedule future start
        process = Process(self, "start", [])
        event = Event(now + PERIOD, process)

        # actual operations to be performed
        self.orch.timeline.schedule(event)        
        self.perform_measurements()

    
    def perform_measurements(self):

        # Preparation
        self.orch.reset_linear_state(self.tl)

        print("--------------------------------------------------------------")
        print(f"\n  Orchestrator Measurement started at {format(self.tl.now())}\n")
        print("--------------------------------------------------------------")

        for client in self.clients:
            client.protocols[0].start()

        self.orch.protocols[0].start(self.orch)


    def pair_protocol(self):
        
        # Assuming that protocol 0 is the measurement protocol!
        p_orch = self.orch.protocols[0]
        
        protocols_names = []
        clients_names = []
        clients_memory_names = []
        
        for client in self.clients:
            p_client = client.protocols[0]
            protocols_names.append(p_client)
            clients_names.append(client.name)
            clients_memory_names.append(client.resource_manager.memory_names[0])

            p_client.set_others(p_orch.name, orchestrator.name, self.local_memories)

        p_orch.set_others(protocols_names, clients_names, self.local_memories)

    def display_state_information(self):
        print("Local Memories:")
        print("----------------------------------------")
        for i, memory in enumerate(self.local_memories):
            print(f"Memory {memory.name}:")
            print(f"  Entangled Memory: {memory.entangled_memory}")
            print(f"  Quantum state stored in memory{memory.qstate_key+1}:")
            print(f"  {self.tl.quantum_manager.states[i+len(self.local_memories)+1]}")
            print("----------------------------------------")
        
        print("Remote Memories:")
        print("----------------------------------------")
        for i, memory in enumerate(self.remote_memories):
            print(f"Memory {memory.name}:")
            print(f"  Entangled Memory: {memory.entangled_memory}")
            print(f"  Quantum state stored in memory{memory.qstate_key+1}:")
            print(f"  {self.tl.quantum_manager.states[i]}")
            print("----------------------------------------")

if __name__ == "__main__":

    # Choose the number of clients configuration
    NUM_CLIENTS= 6  

    network_config = f"/Users/francesco/Desktop/SeQUeNCe Local/example/QLAN/examples/topologies/qlan_topology_{NUM_CLIENTS}.json"
    
    NUM_PERIODS = 3
    PERIOD = 1e12
    client_nodes = []

    network_topo = QlanStarTopo(network_config)
    tl = network_topo.get_timeline()
    tl.stop_time = PERIOD * NUM_PERIODS
    tl.show_progress = True

    # set log
    log_filename = "qlan_app.log"
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('DEBUG')
    #log.track_module('QlanOrchestratorNode')
    #log.track_module('QlanClientNode')
    log.track_module('timeline')

    for node in network_topo.get_nodes_by_type(QlanStarTopo.ORCHESTRATOR):
        orchestrator = node
    for node in network_topo.get_nodes_by_type(QlanStarTopo.CLIENT):
        client_nodes.append(node)

    app = PeriodicApp(tl=tl, orchestrator=orchestrator, clients=client_nodes)
    #reset_app = ResetApp(node2, start_node_name)
    
    tl.init()
    app.start()
    tl.run()

    # End of simulation quantum state...
    print("\n\n############# SIMULATION ENDED #############\n\n")
    app.display_state_information()