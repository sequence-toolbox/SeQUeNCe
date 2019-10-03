from numpy import random
import math
import statistics

from event import Event
from timeline import Timeline
from BB84 import BB84
import topology
from process import Process
import encoding


if __name__ == "__main__":
    random.seed(1)

    runtime = 1e12
    distances = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # distances in km
    errors = []  # store error rates
    throughputs = []  # store throughputs

    for distance in distances:
        tl = Timeline(runtime)
        qc = topology.QuantumChannel("qc", tl,
                                     distance=distance * 1e3, polarization_fidelity=0.97, attenuation=0.0002)
        cc = topology.ClassicalChannel("cc", tl,
                                       distance=distance * 1e3)

        # Alice
        ls = topology.LightSource("alice.lightsource", tl,
                                  encoding_type=encoding.time_bin, frequency=80e6, mean_photon_num=0.1,
                                  direct_receiver=qc, linewidth=0.5)
        components = {"lightsource": ls, "cchannel": cc, "qchannel": qc}
        alice = topology.Node("alice", tl, components=components)
        qc.set_sender(ls)
        cc.add_end(alice)
        tl.entities.append(alice)

        # Bob
        detectors = [{"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                     {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                     {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10}]
        interferometer = {"path_difference": encoding.time_bin["bin_separation"]}
        switch = {}
        qsd = topology.QSDetector("bob.qsdetector", tl,
                                  encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer,
                                  switch=switch)
        components = {"detector": qsd, "cchannel": cc, "qchannel": qc}
        bob = topology.Node("bob", tl, components=components)
        qc.set_receiver(qsd)
        cc.add_end(bob)
        tl.entities.append(bob)

        # BB84
        bba = BB84("bba", tl, role=0, encoding_type=0)
        bbb = BB84("bbb", tl, role=1, encoding_type=0)
        bba.assign_node(alice)
        bbb.assign_node(bob)
        bba.another = bbb
        bbb.another = bba
        alice.protocol = bba
        bob.protocol = bbb

        process = Process(bba, "generate_key", [256, 10, runtime])
        event = Event(0, process)
        tl.schedule(event)

        tl.run()

        errors.append(statistics.mean(bba.error_rates))
        throughputs.append(statistics.mean(bba.throughputs) * 1e-6)

    print(errors)
    print(throughputs)
