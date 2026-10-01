"""A minimal example to show how to use SeQUeNCe to establish entanglement between two nodes. 
"""
import sequence as sq
from sequence import constants
if __name__ == "__main__":

    sq.EntanglementGenerationA.set_global_type(sq.constants.SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(sq.constants.SINGLE_HERALDED)

    # assume the current working directory is the SeQUeNCe repository root
    network_topo = sq.RouterNetTopo(config_source="docs/source/tutorial/sequence3min/two_node.json")
    tl = network_topo.get_timeline()

    name_to_app = {}
    for router in network_topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER):
        name_to_app[router.name] = sq.RequestApp(router)
    
    tl.init()
    alice = "router_0"
    bob = "router_1"
    name_to_app[alice].start(responder=bob, start_t=1 * constants.SECOND, end_t=2.5 * constants.SECOND, memo_size=1, fidelity=0.8)
    tl.run()

    print(f"Entangled pair count between Alice and Bob: {name_to_app[alice].memory_counter}")
    print(f"The throughput is {name_to_app[alice].get_throughput()} pairs per second")
