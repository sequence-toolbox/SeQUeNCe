import math

import pandas as pd
from numpy import mean
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.qkd.BB84 import pair_bb84_protocols
from sequence.topology.node import QKDNode

if __name__ == "__main__":
    NUM_EXPERIMENTS = 11
    runtime = 6e12

    # open file to store experiment results
    # Path("results/sensitivity").mkdir(parents=True, exist_ok=True)
    # filename = "results/sensitivity/distance_bb84.log"
    # fh = open(filename,'w')

    dist_list = []
    tp_list = []
    error_rate_list = []
    latency_list = []

    for i in range(NUM_EXPERIMENTS):
        distance = max(1000, 10000 * int(i))

        tl = Timeline(runtime)
        tl.show_progress = True

        qc0 = QuantumChannel("qc0", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
        qc1 = QuantumChannel("qc1", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
        cc0 = ClassicalChannel("cc0", tl, distance=distance)
        cc1 = ClassicalChannel("cc1", tl, distance=distance)
        cc0.delay += 10e9  # 10 ms
        cc1.delay += 10e9

        # Alice
        ls_params = {"frequency": 80e6, "mean_photon_num": 0.1}
        alice = QKDNode("alice", tl, stack_size=1)
        alice.set_seed(0)

        for name, param in ls_params.items():
            alice.update_lightsource_params(name, param)

        # Bob
        detector_params = [{"efficiency": 0.8, "dark_count": 10, "time_resolution": 10, "count_rate": 50e6},
                           {"efficiency": 0.8, "dark_count": 10, "time_resolution": 10, "count_rate": 50e6}]
        bob = QKDNode("bob", tl, stack_size=1)
        bob.set_seed(1)

        for i in range(len(detector_params)):
            for name, param in detector_params[i].items():
                bob.update_detector_params(i, name, param)

        qc0.set_ends(alice, bob.name)
        qc1.set_ends(bob, alice.name)
        cc0.set_ends(alice, bob.name)
        cc1.set_ends(bob, alice.name)

        # BB84 config
        pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])

        process = Process(alice.protocol_stack[0], "push", [256, math.inf, 6e12])
        event = Event(0, process)
        tl.schedule(event)

        tl.init()
        tl.run()

        print("completed distance {}".format(distance))

        # record metrics
        bba = alice.protocol_stack[0]

        dist_list.append(distance)
        tp_list.append(mean(bba.throughputs))
        error_rate_list.append(mean(bba.error_rates))
        latency_list.append(bba.latency)

    log = {'Distance': dist_list, "Throughput": tp_list, 'Error_rate': error_rate_list, 'Latency': latency_list}
    df = pd.DataFrame(log)
    df.to_csv('distance_bb84.csv')
