import math

import pandas as pd
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.qkd.BB84 import pair_bb84_protocols
from sequence.qkd.cascade import pair_cascade_protocols
from sequence.topology.node import QKDNode

if __name__ == "__main__":
    NUM_EXPERIMENTS = 10
    runtime = 6e12

    dist_list = []
    tp_list = []
    key_error_list = []
    latency_list = []
    setup_time_list = []
    start_time_list = []
    bb84_latency_list = []

    for id in range(NUM_EXPERIMENTS):
        distance = max(1000, 10000*int(id))

        tl = Timeline(runtime)
        tl.show_progress = True

        qc0 = QuantumChannel("qc0", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
        qc1 = QuantumChannel("qc1", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
        cc0 = ClassicalChannel("cc0", tl, distance=distance)
        cc1 = ClassicalChannel("cc1", tl, distance=distance)
        cc0.delay += 10e9
        cc1.delay += 10e9

        # Alice
        ls_params = {"frequency": 80e6, "mean_photon_num": 0.1}
        alice = QKDNode("alice", tl)
        alice.set_seed(0)
        for name, param in ls_params.items():
            alice.update_lightsource_params(name, param)

        # Bob
        detector_params = [
            {"efficiency": 0.8, "dark_count": 10, "time_resolution": 10,
             "count_rate": 50e6},
            {"efficiency": 0.8, "dark_count": 10, "time_resolution": 10,
             "count_rate": 50e6}]
        bob = QKDNode("bob", tl)
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
        # cascade config
        pair_cascade_protocols(alice.protocol_stack[1], bob.protocol_stack[1])

        process = Process(alice.protocol_stack[1], 'push',
                          [256, math.inf, 6e12])
        tl.schedule(Event(0, process))

        tl.init()
        tl.run()

        print("completed distance {}".format(distance))

        # log results
        bba = alice.protocol_stack[0]
        cascade_a = alice.protocol_stack[1]

        dist_list.append(distance)
        tp_list.append(cascade_a.throughput)
        key_error_list.append(cascade_a.error_bit_rate)
        latency_list.append(cascade_a.latency)
        setup_time_list.append(cascade_a.setup_time)
        start_time_list.append(cascade_a.start_time)
        bb84_latency_list.append(bba.latency)

    log = {"Distance": dist_list, "Throughput": tp_list, "Key_error": key_error_list, "Latency": latency_list,
           "Setup_time": setup_time_list, "Start_time": start_time_list, "BB84_latency": bb84_latency_list}
    df = pd.DataFrame(log)
    df.to_csv("distance_cascade.csv")
