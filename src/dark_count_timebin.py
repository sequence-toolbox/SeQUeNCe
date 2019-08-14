from numpy import random
import math
import statistics

from event import Event
from timeline import Timeline
from BB84 import BB84
from cascade import Cascade
import topology
from process import Process
import encoding


if __name__ == "__main__":
    random.seed(1)

    runtime = math.inf
    dark_count = 425
    distances = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]  # distances in km
    errors = []  # store error rates
    throughputs = []  # store throughputs
    throughputs_cascade = []
    throughputs_privacy = []
    latencies_privacy = []

    filename = "results/timebin/distance_cascade.log"
    fh = open(filename, 'w')

    for distance in distances:
        tl = Timeline(runtime)
        qc = topology.QuantumChannel("qc", tl,
                                     distance=distance * 1e3, attenuation=0.0002)
        cc = topology.ClassicalChannel("cc", tl,
                                       distance=distance * 1e3)

        # Alice
        ls = topology.LightSource("alice.lightsource", tl,
                                  frequency=2e6, mean_photon_num=0.1, direct_receiver=qc,
                                  encoding_type=encoding.time_bin)
        components = {"lightsource": ls, "cchannel": cc, "qchannel": qc}
        alice = topology.Node("alice", tl, components=components)
        qc.set_sender(ls)
        cc.add_end(alice)

        # Bob
        detectors = [{"efficiency": 0.072, "dark_count": dark_count, "time_resolution": 10},
                     {"efficiency": 0.072, "dark_count": dark_count, "time_resolution": 10},
                     {"efficiency": 0.072, "dark_count": dark_count, "time_resolution": 10}]
        interferometer = {"path_difference": encoding.time_bin["bin_separation"]}
        switch = {}
        qsd = topology.QSDetector("bob.qsdetector", tl,
                                  encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer,
                                  switch=switch)
        components = {"detector": qsd, "cchannel": cc, "qchannel": qc}
        bob = topology.Node("bob", tl, components=components)
        qc.set_receiver(qsd)
        cc.add_end(bob)

        # add entities
        tl.entities.append(alice)
        tl.entities.append(bob)
        for key in alice.components:
            tl.entities.append(alice.components[key])
        for key in bob.components:
            tl.entities.append(bob.components[key])

        # BB84
        bba = BB84("bba", tl, role=0)
        bbb = BB84("bbb", tl, role=1)
        bba.assign_node(alice)
        bbb.assign_node(bob)
        bba.another = bbb
        bbb.another = bba
        alice.protocol = bba
        bob.protocol = bbb

        # # Cascade
        cascade_a = Cascade("cascade_a", tl, bb84=bba, role=0)
        cascade_b = Cascade("cascade_b", tl, bb84=bbb, role=1)
        cascade_a.assign_cchannel(cc)
        cascade_b.assign_cchannel(cc)
        cascade_a.another = cascade_b
        cascade_b.another = cascade_a
        bba.add_parent(cascade_a)
        bbb.add_parent(cascade_b)

        process = Process(cascade_a, "generate_key", [256, 10, math.inf])
        event = Event(0, process)
        tl.schedule(event)

        tl.init()
        tl.run()

        if bba.error_rates:
            error = statistics.mean(bba.error_rates)
        else:
            error = None

        if bba.throughputs:
            throughput = statistics.mean(bba.throughputs)
        else:
            throughput = None

        throughput_cascade = cascade_a.throughput
        throughput_privacy = cascade_a.privacy_throughput
        latency_privacy = cascade_a.latency

        print("{} km:".format(distance))
        print("\tbb84 error:\t\t\t{}".format(error))
        print("\tbb84 throughput:\t{}".format(throughput))
        print("\tcascade throughput:\t{}".format(throughput_cascade))
        print("\tprivacy throughput:\t{}".format(throughput_privacy))
        print("\tprivacy latency:\t{}".format(latency_privacy))

        errors.append(error)
        throughputs.append(throughput)
        throughputs_cascade.append(throughput_cascade)
        throughputs_privacy.append(throughput_privacy)
        latencies_privacy.append(latency_privacy)

        fh.write(str(distance))
        fh.write(' ')
        fh.write(str(error))
        fh.write(' ')
        fh.write(str(throughput))
        fh.write(' ')
        fh.write(str(throughput_cascade))
        fh.write(' ')
        fh.write(str(throughput_privacy))
        fh.write(' ')
        fh.write(str(latency_privacy))
        fh.write('\n')

    print(errors)
    print(throughputs)
    print(throughputs_cascade)
    print(throughputs_privacy)
    print(latencies_privacy)
