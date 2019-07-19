from numpy import random
import math
from event import Event
from timeline import Timeline
from BB84 import BB84
from cascade import Cascade
import topology
from process import Process

if __name__ == "__main__":
    random.seed(2)
    import sys
    id = sys.argv[1]
    filename = "results/sensitivity/distance_cascade_"+id+".log"
    fh = open(filename,'w')
    distance = max(1000,10000*int(id))

    tl = Timeline(1.2*1e12)
    qc = topology.QuantumChannel("qc", tl, distance=distance, polarization_fidelity=0.97, attenuation=0.0002)
    cc = topology.ClassicalChannel("cc", tl, distance=distance)
    cc.delay += 10**9

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

    # Cascade
    cascade_a = Cascade("cascade_a", tl, bb84=bba, role=0)
    cascade_b = Cascade("cascade_b", tl, bb84=bbb, role=1)
    cascade_a.assign_cchannel(cc)
    cascade_b.assign_cchannel(cc)
    cascade_a.another = cascade_b
    cascade_b.another = cascade_a
    bba.add_parent(cascade_a)
    bbb.add_parent(cascade_b)

    #cascade_a.logflag = True

    process = Process(cascade_a, 'generate_key', [256,math.inf,1.2*10**12])
    tl.schedule(Event(0, process))
    tl.run()

    fh.write(str(distance))
    fh.write(' ')
    fh.write(str(cascade_a.throughput))
    fh.write(' ')
    fh.write(str(cascade_a.error_bit_rate))
    fh.write(' ')
    fh.write(str(cascade_a.latency/1e12))
    fh.write(' ')
    fh.write(str(cascade_a.setup_time/1e12))
    fh.write(' ')
    fh.write(str(cascade_a.start_time/1e12))
    fh.write(' ')
    fh.write(str(bba.latency))
    fh.write('\n')
    fh.close()

