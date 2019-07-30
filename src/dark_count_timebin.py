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

    runtime = 30e12
    dark_count = 432
    distances = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]  # distances in km
    errors = []  # store error rates
    throughputs = []  # store throughputs

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

        process = Process(bba, "generate_key", [256, 10, runtime])
        event = Event(0, process)
        tl.schedule(event)

        tl.init()
        tl.run()

        error = statistics.mean(bba.error_rates)
        errors.append(error)
        print("{}km: {}".format(distance, error))
        throughputs.append(statistics.mean(bba.throughputs) * 1e-3)
