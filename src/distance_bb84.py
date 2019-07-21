from numpy import random
import math
from event import Event
from timeline import Timeline
from BB84 import BB84
import topology
from process import Process

if __name__ == "__main__":
    random.seed(1)
    import sys
    id = sys.argv[1]
    filename = "results/sensitivity/distance_bb84_"+id+".log"
    fh = open(filename,'w')
    distance = max(1000,10000*int(id))

    tl = Timeline(6*1e12)
    qc = topology.QuantumChannel("qc", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
    cc = topology.ClassicalChannel("cc", tl, distance=distance)
    cc.delay+= 10**9

    # Alice
    ls = topology.LightSource("alice.lightsource", tl, frequency=80*10**6, mean_photon_num=0.1, direct_receiver=qc)
    components = {"lightsource": ls, "cchannel":cc, "qchannel":qc}
    alice = topology.Node("alice", tl, components=components)
    qc.set_sender(ls)
    cc.add_end(alice)
    tl.entities.append(alice)

    # Bob
    detectors = [{"efficiency":0.8, "dark_count":10, "time_resolution":10, "count_rate":50*10**6},
                 {"efficiency":0.8, "dark_count":10, "time_resolution":10, "count_rate":50*10**6}]
    splitter = {}
    qsd = topology.QSDetector("bob.qsdetector", tl, detectors=detectors, splitter=splitter)
    components = {"detector":qsd, "cchannel":cc, "qchannel":qc}
    bob = topology.Node("bob",tl,components=components)
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

    process = Process(bba, "generate_key", [256,math.inf,6*10**12])
    event = Event(0,process)
    tl.schedule(event)
    tl.run()

    fh.write(str(distance))
    fh.write(' ')
    fh.write(str(sum(bba.throughputs) / len(bba.throughputs)))
    fh.write(' ')
    fh.write(str(sum(bba.error_rates) / len(bba.error_rates)))
    fh.write(' ')
    fh.write(str(bba.latency))
    fh.write('\n')
    fh.close()
