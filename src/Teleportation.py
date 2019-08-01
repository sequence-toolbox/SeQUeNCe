import numpy
import re
import math

import encoding
import topology
from timeline import Timeline
from entity import Entity
from process import Process
from event import Event


class Teleportation(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", -1)

        self.quantum_delay = 0
        self.classical_delay = 0
        self.measurement_delay = 0
        self.light_time = 0
        self.start_time = 0
        self.bits = []
        self.node = None
        self.parent = None
        self.another_alice = None
        self.another_bob = None
        self.another_charlie = None
        self.quantum_state = [complex(1), complex(0)]
        self.sample_size = 0

    def init(self):
        pass

    def assign_node(self, node):
        self.node = node
        cchannel = node.components.get("cchannel")
        qchannel = node.components.get("qchannel")
        if cchannel is not None:
            self.classical_delay = cchannel.delay
        if qchannel is not None:
            self.quantum_delay = int(round(qchannel.distance / qchannel.light_speed))

    def add_parent(self, parent):
        self.parent = parent

    def emit_photons(self, state, num_photons):
        # current node bob: send photons
        self.node.send_photons(state, num_photons, "lightsource")
        self.light_time = num_photons / self.node.components["lightsource"].frequency
        self.start_time = self.timeline.now()

        # tell charlie that we're sending photons
        self.node.send_message("sending_photons {} {}".format(self.start_time, self.light_time))

    def end_photons(self):
        res = self.node.components["bsm"].get_bsm_res()
        self.node.send_message("bsm_res {}".format(res), "cc_b")

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "sending_photons":  # (current node is Charlie): schedule sending of bsm measurements
            self.light_time = float(message[2])

            process = Process(self, "end_photons", [])
            event = Event(int(message[1]) + self.quantum_delay + round(self.light_time * 1e12), process)
            self.timeline.schedule(event)

        if message[0] == "bsm_res":  # (current node is Bob): get bits w/ bell state measure
            frequency = self.node.components["lightsource"].frequency

            # parse bsm results
            times_and_bits = []  # list of alternating time/bit
            if message[1] != "[]":
                for val in message[1:]:
                    times_and_bits.append(int(re.sub("[],[]", "", val)))
            bsm_res = []
            bsm_single = []
            for i, val in enumerate(times_and_bits):
                bsm_single.append(val)
                if i % 2:
                    bsm_res.append(bsm_single)
                    bsm_single = []

            # calculate bit values
            bits = self.node.get_bits(self.light_time, self.start_time + self.measurement_delay, frequency, "detector")

            # check matching bits between bsm/bits and append to self.bits
            for res in bsm_res:
                index = int(round((res[0] - self.start_time - self.quantum_delay) * frequency * 1e-12))
                if bits[index] != -1:
                    self.bits.append(1 - bits[index])  # flip bits since bsm measures psi+ or psi- states

            # check if we have enough samples, if not run again
            print("bit length: {}".format(len(self.bits)))
            if len(self.bits) >= self.sample_size:
                sample = self.bits[0:self.sample_size - 1]
                del self.bits[0:self.sample_size - 1]
                alpha = sample.count(0) / len(sample)
                beta = sample.count(1) / len(sample)
                print("% 0:\t{}".format(alpha * 100))
                print("% 1:\t{}".format(beta * 100))
                print("time (ms): {}".format(self.timeline.now() * 1e-9))
            else:
                self.another_alice.send_state(self.quantum_state, self.sample_size)

    def send_state(self, quantum_state, sample_size):
        numpy.set_printoptions(threshold=math.inf)

        self.quantum_state = quantum_state
        self.another_bob.quantum_state = quantum_state
        self.sample_size = sample_size
        self.another_bob.sample_size = sample_size
        lightsource = self.node.components["lightsource"]

        start_time = self.timeline.now() + max(0, self.another_bob.quantum_delay - self.quantum_delay)
        bob_start_time = self.timeline.now() + max(0, self.quantum_delay - self.another_bob.quantum_delay)

        # schedule self to emit photons
        num_photons = round(self.sample_size / lightsource.mean_photon_num)
        process = Process(self.node, "send_photons", [self.quantum_state, num_photons, "lightsource"])
        event = Event(start_time, process)
        self.timeline.schedule(event)

        # schedule bob to emit photons
        process = Process(self.another_bob, "emit_photons", [self.quantum_state, num_photons])
        event = Event(bob_start_time, process)
        self.timeline.schedule(event)


# TODO: find a better way to implement
class BSMAdapter(Entity):
    def __init__(self, timeline, **kwargs):
        super().__init__("", timeline)
        self.receiver = kwargs.get("bsm", None)
        self.photon_type = kwargs.get("photon_type", -1)

    def init(self):
        pass

    def get(self, photon):
        self.receiver.get(photon, self.photon_type)


if __name__ == "__main__":
    numpy.random.seed(1)

    tl = Timeline(1e12)

    alice_length = 5e3
    bob_length = 10e3

    qc_ac = topology.QuantumChannel("qc_ac", tl, distance=alice_length)
    qc_bc = topology.QuantumChannel("qc_bc", tl, distance=bob_length)
    cc_ac = topology.ClassicalChannel("cc_ac", tl, distance=alice_length)
    cc_bc = topology.ClassicalChannel("cc_bc", tl, distance=bob_length)

    # Alice
    ls = topology.LightSource("alice.lightsource", tl,
                              frequency=80e6, mean_photon_num=0.1, encoding_type=encoding.time_bin,
                              direct_receiver=qc_ac)
    components = {"lightsource": ls, "qchannel": qc_ac, "cchannel": cc_ac}

    alice = topology.Node("alice", tl, components=components)

    qc_ac.set_sender(ls)
    cc_ac.add_end(alice)

    # Bob
    internal_cable = topology.QuantumChannel("bob.internal_cable", tl,
                                             distance=bob_length)
    spdc = topology.SPDCSource("bob.lightsource", tl,
                               frequency=80e6, mean_photon_num=0.1, encoding_type=encoding.time_bin,
                               direct_receiver=qc_bc, another_receiver=internal_cable, wavelengths=[1532, 795])
    detectors = [{"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                 None,
                 None]
    interferometer = {}
    switch = {}
    qsd = topology.QSDetector("bob.qsdetector", tl,
                              encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer,
                              switch=switch)
    internal_cable.set_sender(spdc)
    internal_cable.set_receiver(qsd)
    internal_cable.distance += 10
    components = {"lightsource": spdc, "detector": qsd, "qchannel": qc_bc, "cchannel": cc_bc}

    bob = topology.Node("bob", tl, components=components)

    qc_bc.set_sender(spdc)
    cc_bc.add_end(bob)

    # Charlie
    detectors = [{"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                 {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10}]
    bsm = topology.BSM("charlie.bsm", tl,
                       encoding_type=encoding.time_bin, detectors=detectors)
    a0 = BSMAdapter(tl, photon_type=0, bsm=bsm)
    a1 = BSMAdapter(tl, photon_type=1, bsm=bsm)
    components = {"bsm": bsm, "qc_a": qc_ac, "qc_b": qc_bc, "cc_a": cc_ac, "cc_b": cc_bc}
    charlie = topology.Node("charlie", tl, components=components)

    qc_ac.set_receiver(a0)
    qc_bc.set_receiver(a1)
    cc_ac.add_end(charlie)
    cc_bc.add_end(charlie)

    # Teleportation
    ta = Teleportation("ta", tl, role=0)
    tb = Teleportation("tb", tl, role=1)
    tc = Teleportation("tc", tl, role=2)

    ta.assign_node(alice)
    tb.assign_node(bob)
    tb.measurement_delay = int(round(internal_cable.distance / internal_cable.light_speed))
    tc.assign_node(charlie)
    tc.quantum_delay = int(round(qc_bc.distance / qc_bc.light_speed))

    ta.another_bob = tb
    ta.another_charlie = tc
    tb.another_alice = ta
    tb.another_charlie = tc
    tc.another_alice = ta
    tc.another_bob = tb

    alice.protocol = ta
    bob.protocol = tb
    charlie.protocol = tc

    # run
    process = Process(ta, "send_state", [[complex(1), complex(0)], 100])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()

