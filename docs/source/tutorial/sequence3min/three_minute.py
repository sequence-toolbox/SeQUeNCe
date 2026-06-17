"""A minimal example to show how to use SeQUeNCe to establish entanglement between two nodes. 
"""
from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED, SECOND
from sequence.entanglement_management.generation import EntanglementGenerationA, EntanglementGenerationB

if __name__ == "__main__":

    EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)

    network_topo = RouterNetTopo(config_source="docs/source/tutorial/sequence3min/two_node.json")
    tl = network_topo.get_timeline()

    name_to_app = {}
    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        name_to_app[router.name] = RequestApp(router)
    
    tl.init()
    alice = "router_0"
    bob = "router_1"
    name_to_app[alice].start(responder=bob, start_t=1 * SECOND, end_t=2.5 * SECOND, memo_size=1, fidelity=0.8)
    tl.run()

    print(f"Entangled pair count between Alice and Bob: {name_to_app[alice].memory_counter}")
    print(f"The throughput is {name_to_app[alice].get_throughput()} pairs per second")
