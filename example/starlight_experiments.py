from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence.topology import Node

import pandas as pd
from sequence.app.random_request import RandomRequestApp
from sequence.topology.router_net_topo import RouterNetTopo


def get_component(node: "Node", component_type: str):
    for comp in node.components.values():
        if type(comp).__name__ == component_type:
            return comp

    raise ValueError("No component of type {} on node {}".format(component_type, node.name))


if __name__ == "__main__":
    # Experiment params and config
    network_config_file = "example/starlight.json"
    network_topo = RouterNetTopo(network_config_file)
    tl = network_topo.get_timeline()
    tl.show_progress = True
    routers = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    bsm_nodes = network_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)

    # set memory parameters
    MEMO_FREQ = 2e3
    MEMO_EXPIRE = 1.3
    MEMO_EFFICIENCY = 0.75
    MEMO_FIDELITY = 0.9349367588934053
    for node in routers:
        memory_array = node.get_components_by_type("MemoryArray")[0]  # assume only 1 memory array
        memory_array.update_memory_params("frequency", MEMO_FREQ)
        memory_array.update_memory_params("coherence_time", MEMO_EXPIRE)
        memory_array.update_memory_params("efficiency", MEMO_EFFICIENCY)
        memory_array.update_memory_params("raw_fidelity", MEMO_FIDELITY)

    # set detector parameters
    DETECTOR_EFFICIENCY = 0.8
    DETECTOR_COUNT_RATE = 5e7
    DETECTOR_RESOLUTION = 100
    for node in bsm_nodes:
        bsm = node.get_components_by_type("SingleAtomBSM")[0]
        bsm.update_detectors_params("efficiency", DETECTOR_EFFICIENCY)
        bsm.update_detectors_params("count_rate", DETECTOR_COUNT_RATE)
        bsm.update_detectors_params("time_resolution", DETECTOR_RESOLUTION)

    # set quantum channel parameters
    ATTENUATION = 0.0002
    QC_FREQ = 1e11
    for qc in network_topo.get_qchannels():
        qc.attenuation = ATTENUATION
        qc.frequency = QC_FREQ

    # set entanglement swapping parameters
    SWAP_SUCC_PROB = 0.64
    SWAP_DEGRADATION = 0.99
    for node in routers:
        node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
        node.network_manager.protocol_stack[1].set_swapping_degradation(SWAP_DEGRADATION)

    apps = []
    router_names = [node.name for node in routers]
    for i, node in enumerate(routers):
        app_node_name = node.name
        others = router_names[:]
        others.remove(app_node_name)
        app = RandomRequestApp(node, others, i,
                               min_dur=1e13, max_dur=2e13, min_size=10,
                               max_size=25, min_fidelity=0.8, max_fidelity=1.0)
        apps.append(app)
        app.start()

    tl.init()
    tl.run()

    for app in apps:
        print(app.node.name)
        for reserve, wait_t, tp in zip(app.reserves, app.get_wait_time(),
                                       app.get_all_throughput()):
            print("    responder={}, start time={} sec, end time={} sec, "
                  "used memory={}, fidelity thredshold={}, wait time={} sec, "
                  "throughput={} pairs/sec".format(reserve[0],
                                                   reserve[1] / 1e12,
                                                   reserve[2] / 1e12,
                                                   reserve[3],
                                                   reserve[4],
                                                   wait_t / 1e12, tp))

    initiators = []
    responders = []
    start_times = []
    end_times = []
    memory_sizes = []
    fidelities = []
    wait_times = []
    throughputs = []
    for node in routers:
        initiator = node.name
        reserves = node.app.reserves
        _wait_times = node.app.get_wait_time()
        _throughputs = node.app.get_all_throughput()
        min_size = min(len(reserves), len(_wait_times), len(_throughputs))
        reserves = reserves[:min_size]
        _wait_times = _wait_times[:min_size]
        _throughputs = _throughputs[:min_size]
        for reservation, wait_time, throughput in zip(reserves, _wait_times,
                                                      _throughputs):
            responder, s_t, e_t, size, fidelity = reservation
            initiators.append(initiator)
            responders.append(responder)
            start_times.append(s_t)
            end_times.append(e_t)
            memory_sizes.append(size)
            fidelities.append(fidelity)
            wait_times.append(wait_time)
            throughputs.append(throughput)
    log = {"Initiator": initiators, "Responder": responders,
           "Start_time": start_times, "End_time": end_times,
           "Memory_size": memory_sizes, "Fidelity": fidelities,
           "Wait_time": wait_times, "Throughput": throughputs}

    df = pd.DataFrame(log)
    df.to_csv("request_with_perfect_network.csv")

    node_names = []
    start_times = []
    end_times = []
    memory_sizes = []
    for node in routers:
        node_name = node.name
        for reservation in node.network_manager.protocol_stack[1].accepted_reservation:
            s_t, e_t, size = reservation.start_time, reservation.end_time, reservation.memory_size
            if reservation.initiator != node.name and reservation.responder != node.name:
                size *= 2
            node_names.append(node_name)
            start_times.append(s_t)
            end_times.append(e_t)
            memory_sizes.append(size)
    log = {"Node": node_names, "Start_time": start_times,
           "End_time": end_times, "Memory_size": memory_sizes}
    df = pd.DataFrame(log)
    df.to_csv("memory_usage_with_perfect_network.csv")
