from numpy import random
from pathlib import Path
import math

import sequence
from sequence.topology.node import QKDNode
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.kernel.timeline import Timeline
from sequence.protocols.qkd.BB84 import *
from sequence.protocols.qkd.cascade import *
from sequence.components.optical_channel import *


if __name__ == "__main__":
    random.seed(2)

    NUM_EXPERIMENTS = 10
    runtime = 1e12

    # open file to store experiment results
    Path("results/sensitivity").mkdir(parents=True, exist_ok=True)
    filename = "results/sensitivity/distance_cascade.log"
    fh = open(filename,'w')

    for id in range(NUM_EXPERIMENTS):
        distance = max(1000,10000*int(id))

        tl = Timeline(runtime)
        qc = QuantumChannel("qc", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
        cc = ClassicalChannel("cc", tl, distance=distance)
        cc.delay += 10e9

        # Alice
        ls_params = {"frequency": 80e6, "mean_photon_num": 0.1}
        alice = QKDNode("alice", tl)
        for name, param in ls_params.items():
            alice.update_lightsource_params(name, param)

        # Bob
        detector_params = [{"efficiency": 0.8, "dark_count": 10, "time_resolution": 10, "count_rate": 50e6},
                           {"efficiency": 0.8, "dark_count": 10, "time_resolution": 10, "count_rate": 50e6}]
        bob = QKDNode("bob", tl)
        for i in range(len(detector_params)):
            for name, param in detector_params[i].items():
                bob.update_detector_params(i, name, param)

        qc.set_ends(alice, bob)
        cc.set_ends(alice, bob)

        # BB84 config
        pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])
        # cascade config
        pair_cascade_protocols(alice.protocol_stack[1], bob.protocol_stack[1])

        process = Process(alice.protocol_stack[1], 'push', [256, math.inf, 12e12])
        tl.schedule(Event(0, process))

        tl.init()
        tl.run()

        print("completed distance {}".format(distance))

        # log results
        bba = alice.protocol_stack[0]
        bbb = bob.protocol_stack[0]
        cascade_a = alice.protocol_stack[1]
        cascade_b = bob.protocol_stack[1]

        fh.write(str(distance))
        fh.write(' ')
        if cascade_a.throughput: fh.write(str(cascade_a.throughput))
        else: fh.write(str(None))
        fh.write(' ')
        if cascade_a.error_bit_rate: fh.write(str(cascade_a.error_bit_rate))
        else: fh.write(str(None))
        fh.write(' ')
        if cascade_a.latency: fh.write(str(cascade_a.latency/1e12))
        else: fh.write(str(None))
        fh.write(' ')
        if cascade_a.setup_time: fh.write(str(cascade_a.setup_time/1e12))
        else: fh.write(str(None))
        fh.write(' ')
        if cascade_a.start_time: fh.write(str(cascade_a.start_time/1e12))
        else: fh.write(str(None))
        fh.write(' ')
        if bba.latency: fh.write(str(bba.latency))
        else: fh.write(str(None))
        fh.write('\n')

    fh.close()

