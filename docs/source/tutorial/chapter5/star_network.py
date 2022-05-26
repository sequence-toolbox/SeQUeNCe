from sequence.topology.router_net_topo import RouterNetTopo


def set_parameters(topology: RouterNetTopo):
    # set memory parameters
    MEMO_FREQ = 2e3
    MEMO_EXPIRE = 0
    MEMO_EFFICIENCY = 1
    MEMO_FIDELITY = 0.9349367588934053
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        memory_array = node.get_components_by_type("MemoryArray")[0]
        memory_array.update_memory_params("frequency", MEMO_FREQ)
        memory_array.update_memory_params("coherence_time", MEMO_EXPIRE)
        memory_array.update_memory_params("efficiency", MEMO_EFFICIENCY)
        memory_array.update_memory_params("raw_fidelity", MEMO_FIDELITY)

    # set detector parameters
    DETECTOR_EFFICIENCY = 0.9
    DETECTOR_COUNT_RATE = 5e7
    DETECTOR_RESOLUTION = 100
    for node in topology.get_nodes_by_type(RouterNetTopo.BSM_NODE):
        bsm = node.get_components_by_type("SingleAtomBSM")[0]
        bsm.update_detectors_params("efficiency", DETECTOR_EFFICIENCY)
        bsm.update_detectors_params("count_rate", DETECTOR_COUNT_RATE)
        bsm.update_detectors_params("time_resolution", DETECTOR_RESOLUTION)
        
    # set entanglement swapping parameters
    SWAP_SUCC_PROB = 0.90
    SWAP_DEGRADATION = 0.99
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
        node.network_manager.protocol_stack[1].set_swapping_degradation(SWAP_DEGRADATION)
        
    # set quantum channel parameters
    ATTENUATION = 1e-5
    QC_FREQ = 1e11
    for qc in topology.get_qchannels():
        qc.attenuation = ATTENUATION
        qc.frequency = QC_FREQ


if __name__ == "__main__":
    network_config = "star_network.json"

    network_topo = RouterNetTopo(network_config)
    tl = network_topo.get_timeline()

    set_parameters(network_topo)

    # the start and end nodes may be edited as desired
    start_node_name = "end1"
    end_node_name = "end2"
    node1 = node2 = None

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            node1 = router
        elif router.name == end_node_name:
            node2 = router

    nm = node1.network_manager
    nm.request(end_node_name, start_time=1e12, end_time=10e12, memory_size=25, target_fidelity=0.9)

    tl.init()
    tl.run()

    print(start_node_name, "memories")
    print("Index:\tEntangled Node:\tFidelity:\tEntanglement Time:")
    for info in node1.resource_manager.memory_manager:
        print("{:6}\t{:15}\t{:9}\t{}".format(str(info.index),
                                             str(info.remote_node),
                                             str(info.fidelity),
                                             str(info.entangle_time * 1e-12)))
