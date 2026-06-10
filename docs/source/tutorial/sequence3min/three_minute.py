"""A minimal example to show how to use SeQUeNCe to establish entanglement between two nodes. 
"""
from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED, SECOND
from sequence.entanglement_management.generation import EntanglementGenerationA, EntanglementGenerationB


if __name__ == "__main__":

    EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)

    network_config = "docs/source/tutorial/sequence3min/two_node.json"
    network_topo = RouterNetTopo(network_config)
    tl = network_topo.get_timeline()

    # Treat router_0 as Alice and router_1 as Bob.
    alice_name = "router_0"
    bob_name = "router_1"
    alice = None
    bob = None
    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == alice_name:
            alice = router
        elif router.name == bob_name:
            bob = router
    alice_app = RequestApp(alice)
    bob_app = RequestApp(bob)
    
    tl.init()
    start_t = 1 * SECOND
    end_t = 2.5 * SECOND
    memo_size = 1
    fidelity = 0.8
    alice_app.start(responder=bob_name, start_t=start_t, end_t=end_t, memo_size=memo_size, fidelity=fidelity)
    tl.run()

    print(f"Entangled pair count between Alice and Bob: {alice_app.memory_counter}")
    print(f"The throughput is {alice_app.get_throughput()} pairs per second")
