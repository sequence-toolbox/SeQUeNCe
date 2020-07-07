from numpy import random
from pathlib import Path
import math

import sequence
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.qkd.BB84 import *
from sequence.components.optical_channel import *
from sequence.topology.node import *
from sequence.utils.encoding import *

if __name__ == "__main__":
    random.seed(1)

    NUM_EXPERIMENTS = 11
    runtime = 6e12

    # open file to store experiment results
    Path("results/sensitivity").mkdir(parents=True, exist_ok=True)
    filename = "results/sensitivity/distance_bb84.log"
    fh = open(filename,'w')

    for i in range(NUM_EXPERIMENTS):
        distance = max(1000, 10000*int(i))

        tl = Timeline(runtime)
        qc = QuantumChannel("qc", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
        cc = ClassicalChannel("cc", tl, distance=distance)
        cc.delay += 10e9  # 10 ms

        # Alice
        ls_params = {"frequency": 80e6, "mean_photon_num": 0.1}
        alice = QKDNode("alice", tl, stack_size=1)

        for name, param in ls_params.items():
            alice.update_lightsource_params(name, param)

        # Bob
        detector_params = [{"efficiency": 0.8, "dark_count": 10, "time_resolution": 10, "count_rate": 50e6},
                           {"efficiency": 0.8, "dark_count": 10, "time_resolution": 10, "count_rate": 50e6}]
        bob = QKDNode("bob", tl, stack_size=1)

        for i in range(len(detector_params)):
            for name, param in detector_params[i].items():
                bob.update_detector_params(i, name, param)

        qc.set_ends(alice, bob)
        cc.set_ends(alice, bob)

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
        fh.write(str(distance))
        fh.write(' ')
        if bba.throughputs:
            fh.write(str(1e-6 * sum(bba.throughputs) / len(bba.throughputs)))
        else:
            fh.write(str(None))
        fh.write(' ')
        if bba.error_rates:
            fh.write(str(sum(bba.error_rates) / len(bba.error_rates)))
        else:
            fh.write(str(None))
        fh.write(' ')
        fh.write(str(bba.latency))
        fh.write('\n')
