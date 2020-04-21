from numpy import random

from sequence.protocols.qkd.BB84 import pair_bb84_protocols

# For testing BB84 Protocol
from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.topology.node import QKDNode
from sequence.protocols.protocol import Protocol
from sequence.utils.encoding import *


random.seed(0)


# dummy parent class to test BB84 functionality
class Parent(Protocol):
    def __init__(self, own: "Node", keysize: int, role: int):
        Protocol.__init__(self, own, "")
        self.upper_protocols = []
        self.lower_protocols = []
        self.keysize = keysize
        self.role = role
        self.key = 0
        self.counter = 0

    def init(self):
        pass

    def pop(self, msg):
        self.key = msg
        self.counter += 1

    def push(self):
        self.lower_protocols[0].push(self.keysize, 10)

    def received_message(self):
        pass


def test_BB84_polarization(): 
    tl = Timeline(1e12)  # stop time is 1 s

    alice = QKDNode("alice", tl)
    bob = QKDNode("bob", tl)
    pair_bb84_protocols(alice.sifting_protocol, bob.sifting_protocol)

    qc = QuantumChannel("qc", tl, distance=10e3, polarization_fidelity=0.99, attenuation=0.00002)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=10e3, attenuation=0.00002)
    cc.set_ends(alice, bob)

    # Parent
    pa = Parent(alice, 512, "alice")
    pb = Parent(bob, 512, "bob")
    pa.lower_protocols.append(alice.sifting_protocol)
    pb.lower_protocols.append(bob.sifting_protocol)
    alice.sifting_protocol.upper_protocols.append(pa)
    bob.sifting_protocol.upper_protocols.append(pb)

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
    assert pa.counter == pb.counter == 10
    print("latency (s): {}".format(alice.sifting_protocol.latency))
    print("average throughput (Mb/s): {}".format(1e-6 * sum(alice.sifting_protocol.throughputs) / len(alice.sifting_protocol.throughputs)))
    print("bit error rates:")
    for i, e in enumerate(alice.sifting_protocol.error_rates):
        print("\tkey {}:\t{}%".format(i + 1, e * 100))


def test_BB84_time_bin():
    tl = Timeline(1e12)  # stop time is 1 s

    alice = QKDNode("alice", tl, encoding=time_bin)
    bob = QKDNode("bob", tl, encoding=time_bin)
    pair_bb84_protocols(alice.sifting_protocol, bob.sifting_protocol)

    qc = QuantumChannel("qc", tl, distance=10e3, polarization_fidelity=0.99, attenuation=0.00002)
    qc.set_ends(alice, bob)
    cc = ClassicalChannel("cc", tl, distance=10e3, attenuation=0.00002)
    cc.set_ends(alice, bob)

    # Parent
    pa = Parent(alice, 512, "alice")
    pb = Parent(bob, 512, "bob")
    pa.lower_protocols.append(alice.sifting_protocol)
    pb.lower_protocols.append(bob.sifting_protocol)
    alice.sifting_protocol.upper_protocols.append(pa)
    bob.sifting_protocol.upper_protocols.append(pb)

    process = Process(pa, "push", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
    assert pa.counter == pb.counter == 10
    print("latency (s): {}".format(alice.sifting_protocol.latency))
    print("average throughput (Mb/s): {}".format(1e-6 * sum(alice.sifting_protocol.throughputs) / len(alice.sifting_protocol.throughputs)))
    print("bit error rates:")
    for i, e in enumerate(alice.sifting_protocol.error_rates):
        print("\tkey {}:\t{}%".format(i + 1, e * 100))

    # tl = timeline.Timeline(1e11)  # stop time is 100 ms
    #
    # qc = topology.QuantumChannel("qc", tl, distance=10e3, polarization_fidelity=0.99)
    # cc = topology.ClassicalChannel("cc", tl, distance=10e3)
    #
    # # Alice
    # ls = topology.LightSource("alice.lightsource", tl,
    #                           frequency=80e6, mean_photon_num=0.1, direct_receiver=qc,
    #                           encoding_type=encoding.time_bin)
    # components = {"asource": ls, "cchannel": cc, "qchannel": qc}
    #
    # alice = topology.Node("alice", tl, components=components)
    # qc.set_sender(ls)
    # cc.add_end(alice)
    #
    # # Bob
    # detectors = [{"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
    #              {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
    #              {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10}]
    # interferometer = {"path_difference": encoding.time_bin["bin_separation"]}
    # switch = {}
    # qsd = topology.QSDetector("bob.qsdetector", tl,
    #                           encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer,
    #                           switch=switch)
    # components = {"bdetector": qsd, "cchannel": cc, "qchannel": qc}
    #
    # bob = topology.Node("bob", tl, components=components)
    # qc.set_receiver(qsd)
    # cc.add_end(bob)
    #
    # tl.entities.append(alice)
    # tl.entities.append(bob)
    # for key in alice.components:
    #     tl.entities.append(alice.components[key])
    # for key in bob.components:
    #     tl.entities.append(bob.components[key])
    #
    # # BB84
    # bba = BB84("bba", tl, role=0, source_name="asource")
    # bbb = BB84("bbb", tl, role=1, detector_name="bdetector")
    # bba.assign_node(alice)
    # bbb.assign_node(bob)
    # bba.another = bbb
    # bbb.another = bba
    # alice.protocol = bba
    # bob.protocol = bbb
    #
    # # Parent
    # pa = Parent(512, "alice")
    # pb = Parent(512, "bob")
    # pa.child = bba
    # pb.child = bbb
    # bba.add_parent(pa)
    # bbb.add_parent(pb)
    #
    # process = Process(pa, "run", [])
    # event = Event(0, process)
    # tl.schedule(event)
    #
    # tl.init()
    # tl.run()
    #
    # print("latency (s): {}".format(bba.latency))
    # print("average throughput (Mb/s): {}".format(1e-6 * sum(bba.throughputs) / len(bba.throughputs)))
    # print("bit error rates:")
    # for i, e in enumerate(bba.error_rates):
    #     print("\tkey {}:\t{}%".format(i + 1, e * 100))
