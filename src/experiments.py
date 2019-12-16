from numpy.random import seed

from protocols import EntanglementGeneration
from protocols import BBPSSW

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
    # store in nodes
    alice.qchannels = {"charlie": qc_ac}
    bob.qchannels = {"charlie": qc_bc}

    # create memories
    NUM_MEMORIES = 100
    FIDELITY = 0.8
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
    alice.components['MemoryArray'] = alice_memo_array
    bob.components['MemoryArray'] = bob_memo_array
    qc_ac.set_sender(alice_memo_array)
    qc_bc.set_sender(bob_memo_array)

    # create BSM
    detectors = [{"efficiency": 0.7, "dark_count": 0, "time_resolution": 150, "count_rate": 25000000}] * 2
    bsm = topology.BSM("charlie_bsm", tl, encoding_type=encoding.ensemble, detectors=detectors)
    charlie.components['BSM'] = bsm
    qc_ac.set_receiver(bsm)
    qc_bc.set_receiver(bsm)

    # create alice protocol stack
    egA = EntanglementGeneration(alice, middle="charlie", others=["bob"], fidelity=FIDELITY)
    bbpsswA = BBPSSW(alice, threshold=0.9)
    egA.upper_protocols.append(bbpsswA)
    bbpsswA.lower_protocols.append(egA)

    # create bob protocol stack
    egB = EntanglementGeneration(bob, middle="charlie", others=["alice"], fidelity=FIDELITY)
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
    print(egA.memories)
    print(egA.waiting_bsm)
    print(egB.memories)
    print(egB.waiting_bsm)


def linear_topo(n: int, runtime=1e12):
    '''
    n: the number of end nodes
    '''
    UNIT_DELAY = 1e5
    UNIT_DISTANCE = 1e3
    DETECTOR_DARK = 0
    DETECTOR_EFFICIENCY = 0.7
    DETECTOR_TIME_RESOLUTION = 150
    DETECTOR_COUNT_RATE = 25000000
    MEMO_FIDELITY = 0.6
    MEMO_EFFICIENCY = 0.5
    MEMO_ARR_SIZE = 100
    MEMO_ARR_FREQ = int(1e6)
    PURIFICATIOIN_THRED = 0.9

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
        cc = topology.ClassicalChannel(name, tl, distance=UNIT_DISTANCE, delay=UNIT_DELAY)
        cc.set_ends([end_node, node])
        print('add', name, 'to', end_node.name)
        print('add', name, 'to', node.name)

        end_node = end_nodes[i+1]
        # classical channel 2
        name = "cc_%s_%s" % (node.name, end_node.name)
        cc = topology.ClassicalChannel(name, tl, distance=UNIT_DISTANCE, delay=UNIT_DELAY)
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
            distance = (j - i) * 2 * UNIT_DISTANCE
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
        bsm = topology.BSM("bsm_%s" % node.name, tl, encoding_type=encoding.ensemble, detectors=detectors)
        node.assign_bsm(bsm)
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
        node.assign_memory_array(memory_array)
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
            qc = topology.QuantumChannel(name, tl, distance=UNIT_DISTANCE)

            memory_array = node.components['MemoryArray']
            for j, memory in enumerate(memory_array):
                # first half of memory
                if j > len(memory_array) / 2:
                    continue
                memory.direct_receiver=qc

            qc.set_sender(memory_array)
            qc.set_receiver(mid_node.components["BSM"])
            node.assign_qchannel(qc)
            mid_node.assign_qchannel(qc)

        if i < len(mid_nodes):
            mid_node = mid_nodes[i]
            name = "qc_%s_%s" % (mid_node.name, node.name)
            print("add", name)
            qc = topology.QuantumChannel(name, tl, distance=UNIT_DISTANCE)

            memory_array = node.components['MemoryArray']
            for j, memory in enumerate(memory_array):
                # last half of memory
                if j <= len(memory_array) / 2:
                    continue
                memory.direct_receiver=qc
            qc.set_sender(memory_array)
            qc.set_receiver(mid_node.components["BSM"])
            node.assign_qchannel(qc)
            mid_node.assign_qchannel(qc)

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

    # create end nodes protocol stack
    for i, node in enumerate(end_nodes):
        bbpssw = BBPSSW(node, threshold=PURIFICATIOIN_THRED)

        if i > 0:
            mid_node = mid_nodes[i-1]
            neighbor = end_nodes[i-1]
            eg = EntanglementGeneration(node, middle=mid_node.name, others=[neighbor.name], fidelity=MEMO_FIDELITY)
            eg.upper_protocols.append(bbpssw)
            bbpssw.lower_protocols.append(eg)

        if i + 1 < len(end_nodes):
            mid_node = mid_nodes[i]
            neighbor = end_nodes[i+1]
            eg = EntanglementGeneration(node, middle=mid_node.name, others=[neighbor.name], fidelity=MEMO_FIDELITY)
            eg.upper_protocols.append(bbpssw)
            bbpssw.lower_protocols.append(eg)

    for node in end_nodes:
        print(node.name)
        for protocol in node.protocols:
            print("    ", protocol)


    # schedule events

    # start simulation
    tl.init()
    tl.run()


if __name__ == "__main__":
    seed(1)
    # three_node_test()
    linear_topo(3)
