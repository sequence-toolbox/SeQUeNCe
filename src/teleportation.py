import numpy
import re
import math

import encoding
import topology
from timeline import Timeline
from entity import Entity
from process import Process
from event import Event
import sys


class Teleportation(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", -1)

        self.quantum_delay = 0
        self.classical_delay = 0
        self.measurement_delay = 0  # delay between photon source and detector within Bob
        self.light_time = 0
        self.start_time = 0
        self.bits = []
        self.prev_bit_length = 0
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
        self.light_time = (num_photons / self.node.components["lightsource"].frequency) * 100
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
                    if res[1] == 0 or (res[1] == 1 and self.node.components["detector"].state_list[0] == 0):
                        self.bits.append(1 - bits[index])  # flip bits since bsm measures psi- state or psi+ w/ single detector
                    elif res[1] == 1:
                        self.bits.append(bits[index])

            # check if we've increased our bit count, if so give update
            if len(self.bits) > self.prev_bit_length:
                print("bit length: {}".format(len(self.bits)))
                self.prev_bit_length = len(self.bits)
                # alpha = self.bits.count(0) / len(self.bits)
                # beta = self.bits.count(1) / len(self.bits)
                # print("\t% 0:\t{}".format(alpha * 100))
                # print("\t% 1:\t{}".format(beta * 100))

            # check if we have enough samples, if not run again
            if len(self.bits) >= self.sample_size:
                timeline_stop(self.timeline)
                sample = self.bits[0:self.sample_size]
                del self.bits[0:self.sample_size]
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
        process = Process(self.another_bob, "emit_photons", [[complex(math.sqrt(1/2)), complex(math.sqrt(1/2))], num_photons])
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


# TODO: implement in timeline?
def timeline_stop(timeline):
    timeline.events.data = []


# obsolete main function for running of individual teleportation test
if __name__ == "__main__":
    numpy.random.seed(int(sys.argv[4]))

    # user input for basis and Alice's state
    bob_basis = int(sys.argv[1])
    state = sys.argv[2]
    alice_state = [None, None]
    if state == "0":
        alice_state = [complex(1), complex(0)]
    elif state == "1":
        alice_state = [complex(0), complex(1)]
    elif state == "+":
        alice_state = [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]
    elif state == "-":
        alice_state = [complex(math.sqrt(1/2)), complex(-math.sqrt(1/2))]
    else:
        raise Exception("invalid state")
    sample_size = int(sys.argv[3])
    if len(sys.argv) < 6:
        phase_error = 0
    else:
        phase_error = float(sys.argv[5])

    alice_length = 6.2e3
    bob_length = 11.1e3

    # initialize timeline and channels
    tl = Timeline(math.inf)

    qc_ac = topology.QuantumChannel("qc_ac", tl, distance=alice_length, attenuation=0.000986)
    qc_bc = topology.QuantumChannel("qc_bc", tl, distance=bob_length, attenuation=0.000513)
    cc_ac = topology.ClassicalChannel("cc_ac", tl, distance=alice_length)
    cc_bc = topology.ClassicalChannel("cc_bc", tl, distance=bob_length)

    # Alice
    ls = topology.LightSource("alice.lightsource", tl,
                              frequency=80e6, mean_photon_num=0.014, encoding_type=encoding.time_bin,
                              direct_receiver=qc_ac, phase_error=0)
    components = {"lightsource": ls, "qchannel": qc_ac, "cchannel": cc_ac}

    alice = topology.Node("alice", tl, components=components)

    qc_ac.set_sender(ls)
    cc_ac.add_end(alice)

    # Bob
    internal_cable = topology.QuantumChannel("bob.internal_cable", tl,
                                             distance=bob_length+10, attenuation=0.0002)
    spdc = topology.SPDCSource("bob.lightsource", tl,
                               frequency=80e6, mean_photon_num=0.045, encoding_type=encoding.time_bin,
                               direct_receiver=qc_bc, another_receiver=internal_cable, wavelengths=[1532, 795],
                               phase_error=0)
    # (change this to change measurement basis)
    if bob_basis == 0:
        detectors = [{"efficiency": 0.65, "dark_count": 100, "time_resolution": 100},
                     None,
                     None]
    elif bob_basis == 1:
        detectors = [None,
                     {"efficiency": 0.65, "dark_count": 100, "time_resolution": 100},
                     {"efficiency": 0.65, "dark_count": 100, "time_resolution": 100}]
    else:
        raise Exception("incorrect basis for Bob")
    interferometer = {"path_difference": encoding.time_bin["bin_separation"]}
    switch = {"state": bob_basis}
    qsd = topology.QSDetector("bob.qsdetector", tl,
                              encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer,
                              switch=switch)
    internal_cable.set_sender(spdc)
    internal_cable.set_receiver(qsd)
    components = {"lightsource": spdc, "detector": qsd, "qchannel": qc_bc, "cchannel": cc_bc}

    bob = topology.Node("bob", tl, components=components)

    qc_bc.set_sender(spdc)
    cc_bc.add_end(bob)

    # Charlie
    detectors = [{"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000},
                 {"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000}]
    bsm = topology.BSM("charlie.bsm", tl,
                       encoding_type=encoding.time_bin, detectors=detectors, phase_error=phase_error)
    a0 = BSMAdapter(tl, photon_type=0, bsm=bsm)
    a1 = BSMAdapter(tl, photon_type=1, bsm=bsm)
    components = {"bsm": bsm, "qc_a": qc_ac, "qc_b": qc_bc, "cc_a": cc_ac, "cc_b": cc_bc}
    charlie = topology.Node("charlie", tl, components=components)

    qc_ac.set_receiver(a0)
    qc_bc.set_receiver(a1)
    cc_ac.add_end(charlie)
    cc_bc.add_end(charlie)

    tl.entities.append(alice)
    tl.entities.append(bob)
    tl.entities.append(charlie)
    for key in alice.components:
        tl.entities.append(alice.components[key])
    for key in bob.components:
        tl.entities.append(bob.components[key])
    for key in charlie.components:
        tl.entities.append(charlie.components[key])

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

    # Run
    process = Process(ta, "send_state", [alice_state, sample_size])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()

    print("seed: {}".format(int(sys.argv[4])))

