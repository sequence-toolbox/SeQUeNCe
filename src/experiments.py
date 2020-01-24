import math
from numpy.random import seed

from protocols import EntanglementGeneration
from protocols import BBPSSW
from protocols import EntanglementSwapping
from protocols import EndNodeProtocol

import sequence
from sequence import topology
from sequence import timeline
from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


def three_node_test():
    tl = timeline.Timeline()

    # create nodes
    alice = topology.Node("alice", tl)
    bob = topology.Node("bob", tl)
    charlie = topology.Node("charlie", tl)
    nodes = [alice,bob]

    # create classical channels
    cc_ab = topology.ClassicalChannel("cc_ab", tl, distance=2e3, delay=2e5)
    cc_ac = topology.ClassicalChannel("cc_ac", tl, distance=1e3, delay=1e5)
    cc_bc = topology.ClassicalChannel("cc_bc", tl, distance=1e3, delay=1e5)
    # add ends
    cc_ab.set_ends([alice, bob])
    cc_ac.set_ends([alice, charlie])
    cc_bc.set_ends([bob, charlie])

    # create quantum channels
    qc_ac = topology.QuantumChannel("qc_ac", tl, distance=1e3)
    qc_bc = topology.QuantumChannel("qc_bc", tl, distance=1e3)

    # create memories
    NUM_MEMORIES = 10
    FIDELITY = 0.6
    MEMO_FREQ = int(1e6)
    memory_param_alice = {"fidelity": FIDELITY, "direct_receiver": qc_ac}
    memory_param_bob = {"fidelity": FIDELITY, "direct_receiver": qc_bc}
    alice_memo_array = topology.MemoryArray("alice_memory_array", tl,
                                            num_memories=NUM_MEMORIES,
                                            frequency=MEMO_FREQ,
                                            memory_params=memory_param_alice)
    bob_memo_array = topology.MemoryArray("bob_memory_array", tl,
                                          num_memories=NUM_MEMORIES,
                                          frequency=MEMO_FREQ,
                                          memory_params=memory_param_bob)
    alice.assign_component(alice_memo_array, "MemoryArray")
    bob.assign_component(bob_memo_array, "MemoryArray")
    qc_ac.set_sender(alice_memo_array)
    qc_bc.set_sender(bob_memo_array)

    # create BSM
    detectors = [{"efficiency": 1, "dark_count": 0, "time_resolution": 150, "count_rate": 25000000}] * 2
    bsm = topology.BSM("charlie_bsm", tl, encoding_type=encoding.single_atom, detectors=detectors)
    charlie.assign_component(bsm, "BSM")
    qc_ac.set_receiver(bsm)
    qc_bc.set_receiver(bsm)

    # assign quantum channels
    alice.assign_qchannel(qc_ac)
    bob.assign_qchannel(qc_bc)

    # create alice protocol stack
    egA = EntanglementGeneration(alice, middles=["charlie"], others=["bob"], fidelity=FIDELITY)
    bbpsswA = BBPSSW(alice, threshold=0.9)
    egA.upper_protocols.append(bbpsswA)
    bbpsswA.lower_protocols.append(egA)

    # create bob protocol stack
    egB = EntanglementGeneration(bob, middles=["charlie"], others=["alice"], fidelity=FIDELITY)
    bbpsswB = BBPSSW(bob, threshold=0.9)
    egB.upper_protocols.append(bbpsswB)
    bbpsswB.lower_protocols.append(egB)

    # create charlie protocol stack
    egC = EntanglementGeneration(charlie, others=["alice", "bob"])

    # schedule events
    process = Process(egA, "start", [])
    event = Event(0, process)
    tl.schedule(event)

    # start simulation
    tl.init()
    tl.run()

    def print_memory(memoryArray):
        for i, memory in enumerate(memoryArray):
            print(i, memoryArray[i].entangled_memory, memory.fidelity)

    for node in nodes:
        memory = node.components['MemoryArray']
        print(node.name)
        print_memory(memory)


def linear_topo(distances, runtime=1e12, **kwargs):
    '''
    distances: list of distances (in meters) between end nodes
    n: the number of end nodes
    '''
    n = len(distances) + 1
    
    UNIT_DELAY = kwargs.get("unit_delay", 1e5)
    UNIT_DISTANCE = kwargs.get("unit_distance", 1e3)
    DETECTOR_DARK = kwargs.get("detector_dark", 0)
    DETECTOR_EFFICIENCY = kwargs.get("detector_efficiency", 0.7)
    DETECTOR_TIME_RESOLUTION = kwargs.get("detector_time_resolution", 150)
    DETECTOR_COUNT_RATE = kwargs.get("detector_count_rate", 25000000)
    MEMO_FIDELITY = kwargs.get("memo_fidelity", 0.8)
    MEMO_EFFICIENCY = kwargs.get("memo_efficiency", 0.5)
    MEMO_ARR_SIZE = kwargs.get("memo_arr_size", 100)
    MEMO_ARR_FREQ = kwargs.get("memo_arr_freq", int(1e6))
    PURIFICATIOIN_THRED = kwargs.get("purification_thred", 0.9)

    tl = timeline.Timeline(runtime)

    # create end nodes
    end_nodes = []
    for i in range(n):
        node = topology.Node("e%d"%i, tl)
        end_nodes.append(node)

    # create middle nodes
    mid_nodes = []
    for i in range(n-1):
        node = topology.Node("m%d"%i, tl)
        mid_nodes.append(node)

    # create classical channels between middle nodes and end nodes
    for i, node in enumerate(mid_nodes):
        end_node = end_nodes[i]
        # classical channel 1
        name = "cc_%s_%s" % (node.name, end_node.name)
        cc = topology.ClassicalChannel(name, tl, distance=distances[i]/2, delay=UNIT_DELAY)
        cc.set_ends([end_node, node])
        print('add', name, 'to', end_node.name)
        print('add', name, 'to', node.name)

        end_node = end_nodes[i+1]
        # classical channel 2
        name = "cc_%s_%s" % (node.name, end_node.name)
        cc = topology.ClassicalChannel(name, tl, distance=distances[i]/2, delay=UNIT_DELAY)
        cc.set_ends([end_node, node])
        print('add', name, 'to', node.name)
        print('add', name, 'to', end_node.name)

    # create classical channels between end nodes
    for i, node1 in enumerate(end_nodes):
        for j, node2 in enumerate(end_nodes):
            if i >= j:
                continue
            delay = (j - i) * 2 * UNIT_DELAY
            name = "cc_%s_%s" % (node1.name, node2.name)
            distance = sum(distances[i:j])
            cc = topology.ClassicalChannel(name, tl, distance=distance, delay=delay)
            cc.set_ends([node1, node2])
            print('add', name, 'to', node1.name)
            print('add', name, 'to', node2.name)

    for node in end_nodes:
        print(node.name)
        for dst in node.cchannels:
            cchannel = node.cchannels[dst]
            print("    ", dst, cchannel.name, cchannel.ends[0].name, '<->', cchannel.ends[1].name)

    # create BSM
    for node in mid_nodes:
        detectors = [{"efficiency":DETECTOR_EFFICIENCY, "dark_count":DETECTOR_DARK, "time_resolution":DETECTOR_TIME_RESOLUTION, "count_rate":DETECTOR_COUNT_RATE}] * 2
        name = "bsm_%s" % node.name
        bsm = topology.BSM("bsm_%s" % node.name, tl, encoding_type=encoding.single_atom, detectors=detectors)
        node.assign_component(bsm, "BSM")
        print('add', name, 'to', node.name)

    '''
    for node in mid_nodes:
        print(node.name, node.components["BSM"].name)
    '''

    # create quantum memories
    for i, node in enumerate(end_nodes):
        memory_params = {"fidelity":MEMO_FIDELITY, "efficiency":MEMO_EFFICIENCY}
        name = "memory_array_%s" % node.name
        memory_array = topology.MemoryArray(name, tl, num_memories=MEMO_ARR_SIZE,
                                            frequency=MEMO_ARR_FREQ,
                                            memory_params=memory_params)
        node.assign_component(memory_array, "MemoryArray")
        print('add', name, 'to', node.name)

    '''
    for node in end_nodes:
        print(node.name, node.components["MemoryArray"].name)
    '''


    # create quantum channel
    for i, node in enumerate(end_nodes):
        if i > 0:
            mid_node = mid_nodes[i-1]
            name = "qc_%s_%s" % (mid_node.name, node.name)
            print("add", name)
            qc = topology.QuantumChannel(name, tl, distance=distances[i-1]/2)

            memory_array = node.components['MemoryArray']
            for j, memory in enumerate(memory_array):
                # first half of memory
                if j >= len(memory_array) / 2:
                    continue
                memory.direct_receiver=qc

            qc.set_sender(memory_array)
            qc.set_receiver(mid_node.components["BSM"])
            node.assign_qchannel(qc)
            mid_node.assign_qchannel(qc)

            print(qc)
            for memory in qc.sender:
                print("\tmemory {}: {}".format(memory, memory.direct_receiver))

        if i < len(mid_nodes):
            mid_node = mid_nodes[i]
            name = "qc_%s_%s" % (mid_node.name, node.name)
            print("add", name)
            qc = topology.QuantumChannel(name, tl, distance=distances[i]/2)

            memory_array = node.components['MemoryArray']
            for j, memory in enumerate(memory_array):
                # last half of memory
                if j < len(memory_array) / 2:
                    continue
                memory.direct_receiver=qc
            qc.set_sender(memory_array)
            qc.set_receiver(mid_node.components["BSM"])
            node.assign_qchannel(qc)
            mid_node.assign_qchannel(qc)

            print(qc)
            for memory in qc.sender:
                print("\tmemory {}: {}".format(memory, memory.direct_receiver))

    '''
    for node in end_nodes:
        print(node.name)
        for dst in node.qchannels:
            qc = node.qchannels[dst]
            print("    ", dst, qc.sender.name, "->", qc.receiver.name)
    '''

    # create middle nodes protocol stack
    for i, node in enumerate(mid_nodes):
        neighbor1 = end_nodes[i]
        neighbor2 = end_nodes[i+1]
        eg = EntanglementGeneration(node, others=[neighbor1.name, neighbor2.name])
        print("add EntanglementGeneration to", node.name)

    '''
    for node in mid_nodes:
        print(node.name)
        for protocol in node.protocols:
            print("    ", protocol)
    '''

    # create end nodes purification protocols
    for i, node in enumerate(end_nodes):
        bbpssw = BBPSSW(node, threshold=PURIFICATIOIN_THRED)

        middles = []
        others = []
        if i > 0:
            middles.append(mid_nodes[i-1].name)
            others.append(end_nodes[i-1].name)
        if i + 1 < len(end_nodes):
            middles.append(mid_nodes[i].name)
            others.append(end_nodes[i+1].name)

        eg = EntanglementGeneration(node, middles=middles, others=others, fidelity=MEMO_FIDELITY)
        if i % 2 == 1:
            eg.is_start = True  # set "is_start" to true on every other node
        eg.upper_protocols.append(bbpssw)
        bbpssw.lower_protocols.append(eg)

        node.protocols.append(node.protocols.pop(0))

    def add_protocols(node, name1, name2):
        top_protocol = node.protocols[-1]
        es = EntanglementSwapping(node, name1, name2, [])
        top_protocol.upper_protocols.append(es)
        es.lower_protocols.append(top_protocol)
        ep = BBPSSW(node, threshold=PURIFICATIOIN_THRED)
        ep.lower_protocols.append(es)
        es.upper_protocols.append(ep)

    def create_stack(left, right, end_nodes):
        assert int(math.log2(right - left)) == math.log2(right - left)
        k = 1
        while k <= (right - left) / 2:
            m = 0
            pos = k * (2 * m + 1) + left
            while pos + k <= right:
                remote1, remote2 = pos - k, pos + k
                if remote1 == 0:
                    node = end_nodes[remote1]
                    add_protocols(node, '', '')

                node = end_nodes[pos]
                add_protocols(node, end_nodes[remote1].name, end_nodes[remote2].name)

                node = end_nodes[remote2]
                add_protocols(node, '', '')

                m += 1
                pos = k * (2 * m + 1) + left
            k *= 2

    # create end nodes purification and swapping protocols
    left, right = 0, n - 1
    while right - left > 1:
        length = 2 ** int(math.log2(right - left))
        create_stack(left, left + length, end_nodes)
        left = left + length
        if left != right:
            next_length = 2 ** int(math.log2(right - left))
            add_protocols(end_nodes[left], end_nodes[0].name, end_nodes[left + next_length].name)
            add_protocols(end_nodes[0], '', '')
            add_protocols(end_nodes[left + next_length], '', '')

    # update known_nodes for EntanglementSwapping protocols
    for i, node in enumerate(end_nodes):
        ess = [protocol for protocol in node.protocols if type(protocol).__name__ == "EntanglementSwapping"]
        counter = 0
        for j in range(i-1, -1, -1):
            node2 = end_nodes[j]
            ess2 = [protocol for protocol in node2.protocols if type(protocol).__name__ == "EntanglementSwapping"]
            for es in ess2:
                if es.remote2 == node.name:
                    ess[counter].known_nodes.append(node2.name)
                    counter += 1
        counter = 0
        for j in range(i+1, len(end_nodes)):
            node2 = end_nodes[j]
            ess2 = [protocol for protocol in node2.protocols if type(protocol).__name__ == "EntanglementSwapping"]
            for es in ess2:
                if es.remote1 == node.name:
                    ess[counter].known_nodes.append(node2.name)
                    counter += 1

    for node in end_nodes:
        print(node.name)
        for protocol in node.protocols:
            print("    ", protocol)
            print(" "*8, "upper protocols", protocol.upper_protocols)
            print(" "*8, "lower protocols", protocol.lower_protocols)

    # add EndProtocol to end nodes
    curr = end_nodes[0]
    curr_last = curr.protocols[-1]
    end_protocol = EndNodeProtocol(curr)
    end_protocol.lower_protocols.append(curr_last)
    curr_last.upper_protocols.append(end_protocol)

    curr = end_nodes[-1]
    curr_last = curr.protocols[-1]
    end_protocol = EndNodeProtocol(curr)
    end_protocol.lower_protocols.append(curr_last)
    curr_last.upper_protocols.append(end_protocol)

    # schedule events
    for node in end_nodes:
        for protocol in node.protocols:
            if type(protocol).__name__ == "EntanglementGeneration":
                process = Process(protocol, "start", [])
                event = Event(0, process)
                tl.schedule(event)

    # start simulation
    tl.init()
    tl.run()

    def print_memory(memoryArray):
        for i, memory in enumerate(memoryArray):
            print("    memory",  i, memoryArray[i].entangled_memory, memory.fidelity)

    for node in end_nodes:
        memory = node.components['MemoryArray']
        print(node.name)
        print_memory(memory)

    pairs0 = end_nodes[0].protocols[-1].dist_counter
    pairs1 = end_nodes[-1].protocols[-1].dist_counter
    print("END 1 PAIRS:", pairs0)
    print("\tThroughput:", pairs0 / (runtime * 1e-12))
    print("END 2 PAIRS:", pairs1)
    print("\tThroughput:", pairs1 / (runtime * 1e-12))


def experiment(number, param, runtime=1e12): 
    if number == 0:
        distances = [40e3] * 14
        linear_topo(distances, runtime, memo_arr_size=param)

    elif number == 1:
        wis_fermi = [40e3, 40e3, 40e3, 40e3, 40e3, 2e3]
        fermi_arg = [40e3, 8e3]
        arg_uiuc = [40e3, 40e3, 40e3, 40e3, 40e3, 6e3]
        total_distances = wis_fermi + fermi_arg + arg_uiuc

        linear_topo(total_distances, runtime, memo_arr_size=param)


if __name__ == "__main__":
    import sys
    import gc
    import inspect
    seed(1)

    # three_node_test()
    # linear_topo([2e3,2e3], 1e13)

    def by_type(typename):
        return [o for o in gc.get_objects() if type(o).__name__ == typename]
    def count(typename):
        return len(by_type(typename))

    num = int(sys.argv[1])
    param = int(sys.argv[2])
    
    experiment(num, param)
    breakpoint()


