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
            new_cc = ClassicalChannel("cc_" + node.name + "_" + dst, tl, 0, 0, delay=cc.delay + 0.25e9)
            new_cc.set_ends(node, end)

    nodes = [network_topo.nodes["Argonne_2"], network_topo.nodes["Argonne_3"]]
    for node in nodes:
        for dst, cc in network_topo.nodes["Argonne_1"].cchannels.items():
            end = network_topo.nodes[dst]
            if isinstance(end, QuantumRouter) and dst != node.name and dst not in node.cchannels:
                new_cc = ClassicalChannel("cc_" + node.name + "_" + dst, tl, 0, 0, delay=cc.delay + 0.25e9)
                new_cc.set_ends(node, end)

    node = network_topo.nodes["UChicago_HC"]
    for dst, cc in network_topo.nodes["UChicago_PME"].cchannels.items():
        end = network_topo.nodes[dst]
        if isinstance(end, QuantumRouter) and dst != node.name and dst not in node.cchannels:
            new_cc = ClassicalChannel("cc_" + node.name + "_" + dst, tl, 0, 0, delay=cc.delay + 0.25e9)
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
    # MEMO_FREQ = 1e11
    MEMO_EXPIRE = -1
    MEMO_EFFICIENCY = 1
    MEMO_FIDELITY = 0.85
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            # node.memory_array.update_memory_params("frequency", MEMO_FREQ)
            node.memory_array.update_memory_params("coherence_time", MEMO_EXPIRE)
            node.memory_array.update_memory_params("efficiency", MEMO_EFFICIENCY)
            node.memory_array.update_memory_params("raw_fidelity", MEMO_FIDELITY)

    # set detector parameters
    DETECTOR_EFFICIENCY = 1
    DETECTOR_COUNT_RATE = 1e12
    DETECTOR_RESOLUTION = 1
    for name, node in network_topo.nodes.items():
        if isinstance(node, MiddleNode):
            node.bsm.update_detectors_params("efficiency", DETECTOR_EFFICIENCY)
            node.bsm.update_detectors_params("count_rate", DETECTOR_COUNT_RATE)
            node.bsm.update_detectors_params("time_resolution", DETECTOR_RESOLUTION)

    # set quantum channel parameters
    ATTENUATION = 0
    # QC_FREQ = 1e11
    for qc in network_topo.qchannels:
        qc.attenuation = ATTENUATION
        # qc.frequency = QC_FREQ

    # set entanglement swapping parameters
    SWAP_SUCC_PROB = 1
    SWAP_DEGRADATION = 1
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
            node.network_manager.protocol_stack[1].set_swapping_degradation(SWAP_DEGRADATION)

    nodes_name = []
    for name, node in network_topo.nodes.items():
        if isinstance(node, QuantumRouter):
            nodes_name.append(name)

    # apps = []
    # for i, name in enumerate(nodes_name):
    #     app_node_name = name
    #     others = nodes_name[:]
    #     others.remove(app_node_name)
    #     app = RandomRequestApp(network_topo.nodes[app_node_name], others, i)
    #     apps.append(app)
    #     app.start()

    app_node_name = "Argonne_2"
    others = nodes_name[:]
    others.remove(app_node_name)
    app = RandomRequestApp(network_topo.nodes[app_node_name], others, 0)
    app.start()
    print(app_node_name)

    tl.init()
    tl.run()

    print(app.node.name)
    print("  ", len(app.get_wait_time()))
    print("  ", app.get_wait_time())
    throughput = app.get_throughput()
    print("  ", throughput)
    print("  ", sum(throughput) / len(throughput))

    # for app in apps:
    #     print(app.node.name)
    #     print("  ", len(app.get_wait_time()))
    #     print("  ", app.get_wait_time())
    #     throughput = app.get_throughput()
    #     print("  ", throughput)
    #     print("  ", sum(throughput) / len(throughput))
