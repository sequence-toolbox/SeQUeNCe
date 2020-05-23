import pandas as pd
from numpy.random import seed
from sequence.app.random_request import RandomRequestApp
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import QuantumRouter, MiddleNode
from sequence.topology.topology import Topology

if __name__ == "__main__":
    # Experiment params and config
    network_config_file = "example/starlight.json"
    runtime = 1e15

    seed(1)
    tl = Timeline(runtime)
    network_topo = Topology("network_topo", tl)
    network_topo.load_config(network_config_file)

    # update delay between middle node and end node
    for name in network_topo.nodes:
        node = network_topo.nodes[name]
        if isinstance(node, MiddleNode):
            ends = []
            ccs = []
            for dst_name in node.cchannels:
                ends.append(dst_name)
                ccs.append(node.cchannels[dst_name])
            for cc in network_topo.cchannels:
                _ends = [end.name for end in cc.ends]
                if set(_ends) == set(ends):
                    ccs[0].delay = cc.delay // 2
                    ccs[1].delay = cc.delay // 2
                    break

    # create classical channels between [Fermilab_2, Argonne_2, Argonne_3, UChicago_HC] and rest of nodes
    node = network_topo.nodes["Fermilab_2"]
    for dst, cc in network_topo.nodes["Fermilab_1"].cchannels.items():
        end = network_topo.nodes[dst]
        if isinstance(end, QuantumRouter) and dst != node.name and dst not in node.cchannels:
            new_cc = ClassicalChannel("cc_" + node.name + "_" + dst, tl, 0, 0, delay=cc.delay + 0.25e9 + 100)
            new_cc.set_ends(node, end)

    nodes = [network_topo.nodes["Argonne_2"], network_topo.nodes["Argonne_3"]]
    for node in nodes:
        for dst, cc in network_topo.nodes["Argonne_1"].cchannels.items():
            end = network_topo.nodes[dst]
            if isinstance(end, QuantumRouter) and dst != node.name and dst not in node.cchannels:
                new_cc = ClassicalChannel("cc_" + node.name + "_" + dst, tl, 0, 0, delay=cc.delay + 0.25e9 + 100)
                new_cc.set_ends(node, end)

    node = network_topo.nodes["UChicago_HC"]
    for dst, cc in network_topo.nodes["UChicago_PME"].cchannels.items():
        end = network_topo.nodes[dst]
        if isinstance(end, QuantumRouter) and dst != node.name and dst not in node.cchannels:
            new_cc = ClassicalChannel("cc_" + node.name + "_" + dst, tl, 0, 0, delay=cc.delay + 0.25e9 + 100)
            new_cc.set_ends(node, end)

    # display components
    #   nodes can be interated from Topology.nodes.values()
    #   quantum channels from Topology.qchannels
    #   classical channels from Topology.cchannels
    # print("Nodes:")
    # for name, node in network_topo.nodes.items():
    #     print("\t" + name + ": ", node)
    # print("Quantum Channels:")
    # for qc in network_topo.qchannels:
    #     print("\t" + qc.name + ": ", qc)
    # print("Classical Channels:")
    # for cc in network_topo.cchannels:
    #     print("\t" + cc.name + ": ", cc, "\tdelay:", cc.delay)

    # update forwarding table
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            table = network_topo.generate_forwarding_table(name)
            # print(name)
            for dst in table:
                next_node = table[dst]
                node.network_manager.protocol_stack[0].add_forwarding_rule(dst, next_node)
                # print("  ", dst, next_node)

    # set memory parameters
    MEMO_FREQ = 2e4
    MEMO_EXPIRE = 0.8
    MEMO_EFFICIENCY = 0.8
    MEMO_FIDELITY = 0.8
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
        if isinstance(node, MiddleNode):
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
    SWAP_SUCC_PROB = 0.81
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
        app = RandomRequestApp(network_topo.nodes[app_node_name], others, i)
        apps.append(app)
        app.start()

    # app = network_topo.nodes["Argonne_2"].app
    # process = Process(app, "fake_start", ['Argonne_3', 52514940000002.0, 64514940000002.0, 12, 0.7384926989936664])
    # event = Event(51015940000002, process)
    # tl.schedule(event)
    #
    # app = network_topo.nodes["NU"].app
    # process = Process(app, "fake_start", ['StarLight', 52312970000003.0, 65312970000003.0, 22, 0.8574196614977367])
    # event = Event(51313760000003, process)
    # tl.schedule(event)
    #
    # app = network_topo.nodes["Fermilab_2"].app
    # process = Process(app, "fake_start", ['Fermilab_1', 57728640000001.0, 76728640000001.0, 18, 0.8474933965580453])
    # event = Event(56429140000001, process)
    # tl.schedule(event)
    #
    # app = network_topo.nodes["Argonne_3"].app
    # process = Process(app, "fake_start", ['Argonne_1', 58713500000002.0, 77713500000002.0, 12, 0.7868413788529791])
    # event = Event(57314000000002, process)
    # tl.schedule(event)
    #
    # app = network_topo.nodes["StarLight"].app
    # process = Process(app, "fake_start", ['Fermilab_1', 61001770000003.0, 74001770000003.0, 19, 0.8834595409581806])
    # event = Event(59304470000003, process)
    # tl.schedule(event)

    # app = network_topo.nodes["UChicago_HC"].app
    # process = Process(app, "fake_start", ['Argonne_3', 65149760000001.0, 76149760000001.0, 14, 0.7394437536689992])
    # event = Event(63553700000001, process)
    # tl.schedule(event)
    #
    # app = network_topo.nodes["UChicago_PME"].app
    # process = Process(app, "fake_start", ['UChicago_HC', 68071410000002.0, 78071410000002.0, 14, 0.881926602016884])
    # event = Event(66471910000002, process)
    # tl.schedule(event)

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
            _throughputs = node.app.get_throughput()
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
                node_names.append(node_name)
                start_times.append(s_t)
                end_times.append(e_t)
                memory_sizes.append(size)
    log = {"Node": node_names, "Start_time": start_times, "End_time": end_times, "Memory_size": memory_sizes}
    df = pd.DataFrame(log)
    df.to_csv("memory_usage_with_perfect_network.csv")
