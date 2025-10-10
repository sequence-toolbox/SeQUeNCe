from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.qlan_star_topo import QlanStarTopo
from sequence.kernel.timeline import Timeline
import sequence.utils.log as log
from sequence.topology.qlan.orchestrator import QlanOrchestratorNode
from sequence.topology.qlan.client import QlanClientNode


class QlanApp:
    """A simple app for QLAN
       NOTE: this app has access to both orchestrator and each of the clients, it is a 'global app'
    """
    def __init__(self, tl: "Timeline", orchestrator: "QlanOrchestratorNode", clients: list["QlanClientNode"]):
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
        """start measurement at the orchestrator, then schedule a future start() event
        """
        # measure at the orchestrator
        self.perform_measurements()

        # schedule a future event        
        now = self.orch.timeline.now()
        process = Process(self, "start", [])
        event = Event(now + PERIOD, process)
        self.orch.timeline.schedule(event)      

    
    def perform_measurements(self):

        self.orch.reset_linear_state(self.tl)

        print("--------------------------------------------------------------")
        print(f"\n  Orchestrator Measurement started at {format(self.tl.now())}\n")
        print("--------------------------------------------------------------")

        for client in self.clients:
            client.protocols[0].start()

        self.orch.protocols[0].start(self.orch)


    def pair_protocol(self):
        """Directly pair the protocols between the orchestrator and the client
        """
        p_orch = self.orch.protocols[0] # Assuming that protocol 0 is the measurement protocol!
        
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

    NUM_CLIENTS= 3
    network_config = f"example/QLAN/topologies/qlan_topology_{NUM_CLIENTS}.json"

    NUM_PERIODS = 3
    PERIOD = 1e12
    client_nodes = []

    network_topo = QlanStarTopo(network_config)
    tl = network_topo.get_timeline()
    tl.stop_time = PERIOD * NUM_PERIODS
    tl.show_progress = True

    log_filename = "example/qlan/qlan_app.log"
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('DEBUG')
    #log.set_logger_level('INFO')
    
    log.track_module('orchestrator')
    log.track_module('correction')
    log.track_module('measurement')
    log.track_module('client')
    #log.track_module('timeline')

    for node in network_topo.get_nodes_by_type(QlanStarTopo.ORCHESTRATOR):
        orchestrator = node
    for node in network_topo.get_nodes_by_type(QlanStarTopo.CLIENT):
        client_nodes.append(node)

    app = QlanApp(tl=tl, orchestrator=orchestrator, clients=client_nodes)
    
    tl.init()
    app.start()
    tl.run()

    print("\n\n############# SIMULATION ENDED #############\n\n")
    app.display_state_information()