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


def three_node_test(runtime=1e12):
    tl = timeline.Timeline(runtime)

    # create nodes
    alice = topology.Node("alice", tl)
    bob = topology.Node("bob", tl)
    charlie = topology.Node("charlie", tl)
    tl.entities.append(alice)
    tl.entities.append(bob)
    tl.entities.append(charlie)
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
    alice.components['MemoryArray'] = alice_memo_array
    bob.components['MemoryArray'] = bob_memo_array
    qc_ac.set_sender(alice_memo_array)
    qc_bc.set_sender(bob_memo_array)

    # create BSM
    detectors = [{"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000}] * 2
    bsm = topology.BSM("charlie_bsm", tl, encoding_type=encoding.ensemble, detectors=detectors)
    charlie.components['BSM'] = bsm
    qc_ac.set_receiver(bsm)
    qc_bc.set_receiver(bsm)

    # create alice protocol stack
    egA = EntanglementGeneration(alice)
    egA.fidelity = FIDELITY
    bbpsswA = BBPSSW(alice, threshold=0.9)
    egA.upper_protocols.append(bbpsswA)
    bbpsswA.lower_protocols.append(egA)
    alice.protocols.append(egA)
    alice.protocols.append(bbpsswA)

    # create bob protocol stack
    egB = EntanglementGeneration(bob)
    egB.fidelity = FIDELITY
    bbpsswB = BBPSSW(bob, threshold=0.9)
    egB.upper_protocols.append(bbpsswB)
    bbpsswB.lower_protocols.append(egB)
    bob.protocols.append(egB)
    bob.protocols.append(bbpsswB)

    # create charlie protocol stack
    egC = EntanglementGeneration(charlie, end_nodes=[alice, bob])
    charlie.protocols.append(egC)

    # schedule events
    process = Process(egC, "start", [])
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


def multiple_node_test(n: int, runtime=1e12):
    # assert that we have an odd number of nodes
    assert n % 2 == 1, "number of nodes must be odd"

    tl = timeline.Timeline(runtime)

    # create nodes
    nodes = [None] * n
    for i in range(n):
        node = topology.Node("node_{}".format(i), tl)
        tl.entities.append(node)

        # end nodes
        if i % 2 == 1: 
            pass

        # middle nodes
        else:
            pass

    # schedule events

    # start simulation
    tl.init()
    tl.run()


if __name__ == "__main__":
    seed(1)
    three_node_test()


