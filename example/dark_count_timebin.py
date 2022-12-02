import math
import statistics

import pandas as pd
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.protocol import StackProtocol
from sequence.qkd.BB84 import pair_bb84_protocols
from sequence.qkd.cascade import pair_cascade_protocols
from sequence.topology.node import QKDNode, Node
from sequence.utils.encoding import time_bin


# dummy parent class to receive cascade keys and end timeline
class Parent(StackProtocol):
    def __init__(self, own: "Node", keysize: int, keynum: int):
        super().__init__(own, "")
        self.upper_protocols = []
        self.lower_protocols = []
        self.keysize = keysize
        self.keynum = keynum
        self.keycounter = 0

    def init(self):
        pass

    def pop(self, key):
        self.keycounter += 1
        if self.keycounter >= self.keynum:
            self.own.timeline.stop()

    def push(self):
        self.lower_protocols[0].push(self.keysize, self.keynum)

    def received_message(self, src, msg):
        pass


if __name__ == "__main__":
    runtime = math.inf
    dark_count = 425
    distances = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]  # distances in km
    KEYSIZE = 256
    KEYNUM = 10

    errors = []  # store error rates
    throughputs = []  # store throughputs

    # open file to store experiment results
    # Path("results/timebin").mkdir(parents=True, exist_ok=True)
    # filename = "results/timebin/distance_cascade.log"
    # fh = open(filename, 'w')

    for distance in distances:
        tl = Timeline(runtime)
        qc0 = QuantumChannel("qc0", tl, distance=distance * 1e3, attenuation=0.0002)
        qc1 = QuantumChannel("qc1", tl, distance=distance * 1e3, attenuation=0.0002)
        cc0 = ClassicalChannel("cc0", tl, distance=distance * 1e3)
        cc1 = ClassicalChannel("cc1", tl, distance=distance * 1e3)

        # Alice
        ls_params = {"frequency": 2e6, "mean_photon_num": 0.1}
        alice = QKDNode("alice", tl, encoding=time_bin)
        alice.set_seed(0)

        for name, param in ls_params.items():
            alice.update_lightsource_params(name, param)

        # Bob
        detector_params = [{"efficiency": 0.072, "dark_count": dark_count,
                            "time_resolution": 10},
                           {"efficiency": 0.072, "dark_count": dark_count,
                            "time_resolution": 10},
                           {"efficiency": 0.072, "dark_count": dark_count,
                            "time_resolution": 10}]
        bob = QKDNode("bob", tl, encoding=time_bin)
        bob.set_seed(1)

        for i in range(len(detector_params)):
            for name, param in detector_params[i].items():
                bob.update_detector_params(i, name, param)

        qc0.set_ends(alice, bob.name)
        qc1.set_ends(bob, alice.name)
        cc0.set_ends(alice, bob.name)
        cc1.set_ends(bob, alice.name)

        # BB84 and cascade config
        pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])
        pair_cascade_protocols(alice.protocol_stack[1], bob.protocol_stack[1])

        # Parent
        pa = Parent(alice, KEYSIZE, KEYNUM)
        pb = Parent(bob, KEYSIZE, KEYNUM)
        alice.protocol_stack[1].upper_protocols.append(pa)
        pa.lower_protocols.append(alice.protocol_stack[1])
        bob.protocol_stack[1].upper_protocols.append(pb)
        pb.lower_protocols.append(bob.protocol_stack[1])

        process = Process(pa, "push", [])
        event = Event(0, process)
        tl.schedule(event)

        tl.init()
        tl.run()

        # get metrics
        bba = alice.protocol_stack[0]
        cascade_a = alice.protocol_stack[1]

        if bba.error_rates:
            error = statistics.mean(bba.error_rates)
        else:
            error = None

        if bba.throughputs:
            throughput = statistics.mean(bba.throughputs)
        else:
            throughput = None

        print("\n{} km:".format(distance))
        print("\tbb84 error:\t\t\t{}".format(error))
        print("\tbb84 throughput:\t{}".format(throughput))

        errors.append(error)
        throughputs.append(throughput)

        # fh.write(str(distance))
        # fh.write(' ')
        # fh.write(str(error))
        # fh.write(' ')
        # fh.write(str(throughput))
        # fh.write(' ')
        # fh.write(str(throughput_cascade))
        # fh.write(' ')
        # fh.write(str(throughput_privacy))
        # fh.write(' ')
        # fh.write(str(latency_privacy))
        # fh.write('\n')

    log = {'Distance': distances, 'Error_rate': errors, 'Throughput_BB84': throughputs}
    df = pd.DataFrame(log)
    df.to_csv('dark_count_timebin.csv')
