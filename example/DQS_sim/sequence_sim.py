from ghz_app import GHZApp

from sequence.topology.router_net_topo import RouterNetTopo
import sequence.utils.log as log


def run_sequence_simulation(network_config_file, prep_time, cutoff_time, app_info,
                            trial_no=0,
                            logging=False, log_output="results/test_log.log",
                            module_to_log=("timeline", "purification"),
                            verbose_output=False):
    """Main script to run simulation in SeQUeNCe.

    Args:

    Return (Tuple): memory states, memory entanglement, and entanglement times.
    """

    # establish network
    net_topo = RouterNetTopo(network_config_file)

    # timeline setup
    tl = net_topo.get_timeline()
    tl.stop_time = (prep_time + cutoff_time) * 1e12
    # print(f"Simulation length: {tl.stop_time / 1e12} s")

    if logging:
        # set log
        log.set_logger(__name__, tl, log_output)
        log.set_logger_level('DEBUG')
        for module in module_to_log:
            log.track_module(module)

        # TODO: need way to perform this in function
        # elif i == 1:
        #     for module in module_to_log:
        #         log.remove_module(module)

    # network configuration
    routers = net_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    bsm_nodes = net_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)

    for j, node in enumerate(routers + bsm_nodes):
        node.set_seed(j + (trial_no * 3))

    # establish apps
    start_nodes = app_info["start_nodes"]
    end_nodes = app_info["end_nodes"]
    app_memories = app_info["memory_number"]
    apps = []
    for start_name in start_nodes:
        start_node = None
        for node in routers:
            if node.name == start_name:
                start_node = node
                break
        if not start_node:
            raise ValueError(f"Invalid app node name {start_name}")

        apps.append(GHZApp(start_node))

    # initialize and start apps
    tl.init()

    for app, other_node in zip(apps, end_nodes):
        app.start(other_node,
                  prep_time * 1e12,
                  (prep_time + cutoff_time) * 1e12,
                  app_memories,
                  fidelity=1.0)

    # run simulation
    tl.run()

    # get state data for trial
    memory_states = []
    memory_entanglement = []
    memory_times = []

    memo_arr = start_node.get_components_by_type("MemoryArray")[0]
    for index in apps[1].memo_to_reserve:  # iterate through memo indices
        memo = memo_arr[index]
        update_time = memo.last_update_time
        state = memo.get_bds_state()
        remote = memo.entangled_memory['node_id']
        if remote is not None:
            memory_states.append(list(state))  # ndarray not serializable for JSON
            memory_entanglement.append(remote)
            memory_times.append(update_time)

    if verbose_output:
        print("\tMemory states:")
        for index in apps[1].memo_to_reserve:  # iterate through memo indices
            memo = memo_arr[index]
            # state = tl.quantum_manager.get(memo.qstate_key).state
            update_time = memo.last_update_time
            state = memo.get_bds_state()
            remote = memo.entangled_memory['node_id']
            print(f"\t\t{index}: {memo} ({remote})")
            print(f"\t\t\t{state}")
            print(f"\t\t\tUpdate time: {update_time * 1e-12} s")
            print(f"\t\t\tGeneration time: {memo.generation_time * 1e-12} s")

    return memory_states, memory_entanglement, memory_times
