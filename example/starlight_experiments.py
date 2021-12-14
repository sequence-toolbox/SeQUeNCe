import pandas as pd
from sequence.app.random_request import RandomRequestApp
from sequence.kernel.timeline import Timeline
from sequence.topology.node import QuantumRouter, BSMNode
from sequence.topology.topology import Topology

if __name__ == "__main__":
    # Experiment params and config
    network_config_file = "example/starlight.json"
    runtime = 1e15

    tl = Timeline(runtime)
    tl.seed(1)

    network_topo = Topology("network_topo", tl)
    network_topo.load_config(network_config_file)

    # set memory parameters
    MEMO_FREQ = 2e3
    MEMO_EXPIRE = 1.3
    MEMO_EFFICIENCY = 0.75
    MEMO_FIDELITY = 0.9349367588934053
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            node.memory_array.update_memory_params("frequency", MEMO_FREQ)
            node.memory_array.update_memory_params("coherence_time", MEMO_EXPIRE)
            node.memory_array.update_memory_params("efficiency", MEMO_EFFICIENCY)
            node.memory_array.update_memory_params("raw_fidelity", MEMO_FIDELITY)

    # set detector parameters
    DETECTOR_EFFICIENCY = 0.8
    DETECTOR_COUNT_RATE = 5e7
    DETECTOR_RESOLUTION = 100
    for name, node in network_topo.nodes.items():
        if isinstance(node, BSMNode):
            node.bsm.update_detectors_params("efficiency", DETECTOR_EFFICIENCY)
            node.bsm.update_detectors_params("count_rate", DETECTOR_COUNT_RATE)
            node.bsm.update_detectors_params("time_resolution", DETECTOR_RESOLUTION)

    # set quantum channel parameters
    ATTENUATION = 0.0002
    QC_FREQ = 1e11
    for qc in network_topo.qchannels:
        qc.attenuation = ATTENUATION
        qc.frequency = QC_FREQ

    # set entanglement swapping parameters
    SWAP_SUCC_PROB = 0.64
    SWAP_DEGRADATION = 0.99
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
            node.network_manager.protocol_stack[1].set_swapping_degradation(SWAP_DEGRADATION)

    nodes_name = []
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            nodes_name.append(name)

    apps = []
    for i, name in enumerate(nodes_name):
        app_node_name = name
        others = nodes_name[:]
        others.remove(app_node_name)
        app = RandomRequestApp(network_topo.nodes[app_node_name], others, i,
                               min_dur=1e13, max_dur=2e13, min_size=10,
                               max_size=25, min_fidelity=0.8, max_fidelity=1.0)
        apps.append(app)
        app.start()

    tl.init()
    tl.run()

    for app in apps:
        print(app.node.name)
        print("  ", len(app.get_wait_time()))
        print("  ", app.get_wait_time())
        throughput = app.get_throughput()
        print(" ", app.reserves)
        print("  ", throughput)

    initiators = []
    responders = []
    start_times = []
    end_times = []
    memory_sizes = []
    fidelities = []
    wait_times = []
    throughputs = []
    for node in network_topo.nodes.values():
        if isinstance(node, QuantumRouter):
            initiator = node.name
            reserves = node.app.reserves
            _wait_times = node.app.get_wait_time()
            _throughputs = node.app.get_all_throughput()
            min_size = min(len(reserves), len(_wait_times), len(_throughputs))
            reserves = reserves[:min_size]
            _wait_times = _wait_times[:min_size]
            _throughputs = _throughputs[:min_size]
            for reservation, wait_time, throughput in zip(reserves, _wait_times, _throughputs):
                responder, s_t, e_t, size, fidelity = reservation
                initiators.append(initiator)
                responders.append(responder)
                start_times.append(s_t)
                end_times.append(e_t)
                memory_sizes.append(size)
                fidelities.append(fidelity)
                wait_times.append(wait_time)
                throughputs.append(throughput)
    log = {"Initiator": initiators, "Responder": responders, "Start_time": start_times, "End_time": end_times,
           "Memory_size": memory_sizes, "Fidelity": fidelities, "Wait_time": wait_times, "Throughput": throughputs}

    df = pd.DataFrame(log)
    df.to_csv("request_with_perfect_network.csv")

    node_names = []
    start_times = []
    end_times = []
    memory_sizes = []
    for node in network_topo.nodes.values():
        if isinstance(node, QuantumRouter):
            node_name = node.name
            for reservation in node.network_manager.protocol_stack[1].accepted_reservation:
                s_t, e_t, size = reservation.start_time, reservation.end_time, reservation.memory_size
                if reservation.initiator != node.name and reservation.responder != node.name:
                    size *= 2
                node_names.append(node_name)
                start_times.append(s_t)
                end_times.append(e_t)
                memory_sizes.append(size)
    log = {"Node": node_names, "Start_time": start_times, "End_time": end_times, "Memory_size": memory_sizes}
    df = pd.DataFrame(log)
    df.to_csv("memory_usage_with_perfect_network.csv")
