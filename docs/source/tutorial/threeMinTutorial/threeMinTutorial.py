from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED
from sequence.entanglement_management.generation import EntanglementGenerationA, EntanglementGenerationB



if __name__ == "__main__":

    network_config = "docs/source/tutorial/threeMinTutorial/two_node_topology.json" #relative import

    EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)

    network_topo = RouterNetTopo(network_config)
    tl = network_topo.get_timeline()
    tl.stop_time = 3e12
    tl.show_progress = False

    # The topology generator names the routers router_0 and router_1.
    # In this tutorial, we will treat router_0 as Alice and router_1 as Bob.
    alice_node_name = "router_0"
    bob_node_name = "router_1"
    alice = bob = None

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == alice_node_name:
            alice = router
        elif router.name == bob_node_name:
            bob = router


    memory_size = 1
    target_fidelity = 0.6

    alice_app = RequestApp(alice)
    bob_app = RequestApp(bob)

    print("Alice is using node:", alice.name)
    print("Bob is using node:", bob.name)

    tl.init()
    alice_app.start(bob_node_name, int(1e12), int(2e12), memory_size, target_fidelity)
    tl.run()
    if alice_app.memory_counter > 0:
        print("Entanglement established between Alice and Bob")
        print("Alice received", alice_app.memory_counter, "entangled memory pair(s)")
    else:
        print("No entanglement was established between Alice and Bob")
