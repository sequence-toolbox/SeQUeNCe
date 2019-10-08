"""
Network Topology:

(ALICE)===(CHARLIE)===(BOB)

ALICE:
    Detector

CHARLIE:
    2 SPDC Sources
    BSM
    2 Quantum Memories

BOB:
    Detector
"""
import math
import re

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event
from sequence.timeline import Timeline
from sequence import topology


# Protocol
class Swap(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", -1)  # Alice, Bob, Charlie are 0, 1, 2, respectively

        self.classical_delay = 0
        self.quantum_delay = 0
        self.start_time = 0
        self.light_time = 0
        self.qubit_frequency = 0
        self.raw_bit_list = []
        self.bit_list = []
        self.bit_lengths = [None, None]
        self.indices = [None, None]
        self.parent = None
        self.another_alice = None
        self.another_bob = None
        self.another_charlie = None
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

    def begin_photon_pulse(self):
        # reset memories
        memory_alice = self.node.components["memory_a"]
        memory_bob = self.node.components["memory_b"]
        memory_alice.clear_memory()
        memory_bob.clear_memory()
        memory_alice.start_time = self.timeline.now()
        memory_bob.start_time = self.timeline.now()

        # emit photons at both sources
        state = [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]
        num_photons = int(self.light_time * self.qubit_frequency)
        self.node.send_photons(state, num_photons, "spdc_a")
        self.node.send_photons(state, num_photons, "spdc_b")

    def end_photon_pulse(self):
        # get indices of detection events
        bits = self.node.get_bits(self.light_time, self.start_time, self.qubit_frequency, "detector")
        self.raw_bit_list = bits
        indices = [i for i, b in enumerate(bits) if b != -1]

        # send indices to Charlie
        message = "received_photons {} {}".format(self.role, indices)
        self.node.send_message(message)

    def send_to_bsm(self):
        # if [] not in self.indices:
        #     # get indices
        #     index_alice = self.indices[0].pop(0)
        #     index_bob = self.indices[1].pop(0)

        # get index for BSM
        index_bsm = int(round((self.timeline.now() - self.start_time) * self.qubit_frequency * 1e-12))

        if index_bsm < len(self.indices[0]) and index_bsm < len(self.indices[1]):
            index_alice = self.indices[0][index_bsm]
            index_bob = self.indices[1][index_bsm]

            # send corresponding photons to bsm
            memory_alice = self.node.components["memory_a"]
            memory_bob = self.node.components["memory_b"]
            photons_alice = memory_alice.retrieve_photon(index_alice)
            photons_bob = memory_bob.retrieve_photon(index_bob)
            for photon in photons_alice:
                self.node.components["bsm_a"].get(photon)
            for photon in photons_bob:
                self.node.components["bsm_b"].get(photon)

            # schedule next send_to_bsm after 1/qubit_frequency
            time = self.timeline.now() + int(1e12 / self.qubit_frequency)
            process = Process(self, "send_to_bsm", [])
            event = Event(time, process)
            self.timeline.schedule(event)

        else:
            bsm_res = self.node.components["bsm"].get_bsm_res()
            alice_indices_bsm = []
            bob_indices_bsm = []
            for res in bsm_res:
                index_bsm = int(round((res[0] - self.start_time) * self.qubit_frequency * 1e-12))
                alice_indices_bsm.append([self.indices[0][index_bsm], res[1]])
                bob_indices_bsm.append([self.indices[1][index_bsm], res[1]])

            message_alice = "bsm_result {}".format(alice_indices_bsm)
            message_bob = "bsm_result {}".format(bob_indices_bsm)

            self.node.send_message(message_alice, "cc_ac")  # send to Alice
            self.node.send_message(message_bob, "cc_bc")  # send to Bob

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "begin_entanglement_swap":
            # set params
            self.qubit_frequency = float(message[1])
            self.light_time = float(message[2])
            self.start_time = int(message[3]) + self.quantum_delay

            # schedule end_photon_pulse()
            process = Process(self, "end_photon_pulse", [])
            event = Event(self.start_time + int(round(self.light_time * 1e12)), process)
            self.timeline.schedule(event)

            # clear detector photon times to restart measurement
            process = Process(self.node.components["detector"], "clear_detectors", [])
            event = Event(int(self.start_time), process)
            self.timeline.schedule(event)

        if message[0] == "received_photons":
            # parse indices
            indices = []
            if message[2] != "[]":  # no matching indices
                for val in message[2:]:
                    indices.append(int(re.sub("[],[]", "", val)))

            # determine if from Alice or Bob
            # store indices
            sender = int(message[1])  # 0 for Alice and 1 for Bob
            self.indices[sender] = indices

            # see if we have both index lists and if so send to BSM
            if None not in self.indices:
                # set start time (used to determine which bsm result we have in send_to_bsm
                self.start_time = self.timeline.now()
                self.send_to_bsm()

        if message[0] == "bsm_result":
            # parse bsm results
            indices_and_bits = []  # list of alternating time/bit
            if message[1] != "[]":
                for val in message[1:]:
                    indices_and_bits.append(int(re.sub("[],[]", "", val)))
            bsm_res = []
            bsm_single = []
            for i, val in enumerate(indices_and_bits):
                bsm_single.append(val)
                if i % 2:
                    bsm_res.append(bsm_single)
                    bsm_single = []

            # get and correct results
            for res in bsm_res:
                bit = self.raw_bit_list[res[0]]
                if self.role == 1:
                    bit = 1 - bit
                self.bit_list.append(bit)

            # send finished message
            message = "got_bits {} {}".format(self.role, len(self.bit_list))
            self.node.send_message(message)

        if message[0] == "got_bits":
            sender = int(message[1])
            self.bit_lengths[sender] = int(message[2])

            # check if we have both
            if self.bit_lengths[0] == self.bit_lengths[1] and self.bit_lengths[0] is not None:
                if self.bit_lengths[0] < self.sample_size:
                    self.start_protocol()
                else:
                    # finished protocol
                    print("finished entanglement swap")

                    alice_measured = 0
                    alice_bits = self.another_alice.bit_list[:100]
                    for x in alice_bits:
                        if x == 0 or x == 1:
                            alice_measured <<= 1
                            alice_measured |= x
                    bob_measured = 0
                    bob_bits = self.another_bob.bit_list[:100]
                    for x in bob_bits:
                        if x == 0 or x == 1:
                            bob_measured <<= 1
                            bob_measured |= x

                    print("Alice measured bits: \t{}".format(bin(alice_measured)))
                    print("Bob measured bits: \t\t{}".format(bin(bob_measured)))

                    bit_diff = alice_measured ^ bob_measured
                    num_errors = 0
                    while bit_diff:
                        bit_diff &= bit_diff - 1
                        num_errors += 1

                    print("error percentage: {}".format((num_errors / self.sample_size) * 100))

                    self.timeline.stop()

    def start_protocol(self):
        # reset params
        self.indices = [None, None]

        # set start time
        self.start_time = self.timeline.now() + int(max(round(self.another_alice.classical_delay),
                                                        round(self.another_bob.classical_delay)))

        # notify Alice and Bob that we are starting entanglement swap
        message = "begin_entanglement_swap {} {} {}".format(self.qubit_frequency, self.light_time, self.start_time)
        self.node.send_message(message, "cc_ac")  # send to Alice
        self.node.send_message(message, "cc_bc")  # send to Bob

        # schedule start for begin_photon_pulse
        process = Process(self, "begin_photon_pulse", [])
        event = Event(self.start_time, process)
        self.timeline.schedule(event)

    def generate_pairs(self, sample_size):
        # assert that start_protocol is called from Charlie (middle node)
        assert self.role == 2

        self.sample_size = sample_size
        self.bit_lengths = [0, 0]

        # set qubit frequency
        lightsource_a = self.node.components["spdc_a"]
        lightsource_b = self.node.components["spdc_b"]
        assert lightsource_a.frequency == lightsource_b.frequency
        self.qubit_frequency = lightsource_a.frequency
        memory_alice = self.node.components["memory_a"]
        memory_bob = self.node.components["memory_b"]
        memory_alice.frequency = self.qubit_frequency
        memory_bob.frequency = self.qubit_frequency

        # set light_time
        mean_photon_num = min(lightsource_a.mean_photon_num, lightsource_b.mean_photon_num)
        self.light_time = sample_size / (self.qubit_frequency * mean_photon_num)

        self.start_protocol()


# main function to test entanglement_swap protocol
if __name__ == "__main__":
    tl = Timeline()

    # Channels
    qc_alice_charlie = topology.QuantumChannel("qc_ac", tl, distance=1e3, attenuation=.0002)
    qc_bob_charlie = topology.QuantumChannel("qc_bc", tl, distance=1e3, attenuation=0.0002)
    cc_alice_charlie = topology.ClassicalChannel("cc_ac", tl, distance=1e3)
    cc_bob_charlie = topology.ClassicalChannel("cc_bc", tl, distance=1e3)

    # Alice
    detectors = [{"efficiency": 1, "dark_count": 100, "time_resolution": 100},
                 None,
                 None]
    interferometer = {}
    switch = {"state": 0}
    detector_alice = topology.QSDetector("alice.qsd", tl, encoding_type=encoding.time_bin, detectors=detectors,
                                         interferometer=interferometer, switch=switch)
    components = {"detector": detector_alice, "qchannel": qc_alice_charlie, "cchannel": cc_alice_charlie}

    alice = topology.Node("alice", tl, components=components)

    qc_alice_charlie.set_receiver(detector_alice)
    cc_alice_charlie.add_end(alice)

    # Bob
    detectors = [{"efficiency": 1, "dark_count": 100, "time_resolution": 100},
                 None,
                 None]
    interferometer = {}
    switch = {"state": 0}
    detector_bob = topology.QSDetector("bob.qsd", tl, encoding_type=encoding.time_bin, detectors=detectors,
                                       interferometer=interferometer, switch=switch)
    components = {"detector": detector_bob, "qchannel": qc_bob_charlie, "cchannel": cc_bob_charlie}

    bob = topology.Node("bob", tl, components=components)

    qc_bob_charlie.set_receiver(detector_bob)
    cc_bob_charlie.add_end(bob)

    # Charlie
    mem_charlie_1 = topology.IndexedMemory("charlie.mem_1", tl)
    mem_charlie_2 = topology.IndexedMemory("charlie.mem_2", tl)
    spdc_charlie_1 = topology.SPDCSource("charlie.ls_1", tl, frequency=80e6, mean_photon_num=0.045,
                                         encoding_type=encoding.time_bin, direct_receiver=qc_alice_charlie,
                                         another_receiver=mem_charlie_1, wavelengths=[1532, 795], phase_error=0)
    spdc_charlie_2 = topology.SPDCSource("charlie.ls_2", tl, frequency=80e6, mean_photon_num=0.045,
                                         encoding_type=encoding.time_bin, direct_receiver=qc_bob_charlie,
                                         another_receiver=mem_charlie_2, wavelengths=[1532, 795], phase_error=0)
    detectors = [{"efficiency": 1, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000},
                 {"efficiency": 1, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000}]
    bsm_charlie = topology.BSM("charlie.bsm", tl,
                               encoding_type=encoding.time_bin, detectors=detectors, phase_error=0)
    a0 = topology.BSMAdapter(tl, photon_type=0, bsm=bsm_charlie)
    a1 = topology.BSMAdapter(tl, photon_type=1, bsm=bsm_charlie)
    components = {"memory_a": mem_charlie_1, "memory_b": mem_charlie_2, "spdc_a": spdc_charlie_1,
                  "spdc_b": spdc_charlie_2, "bsm": bsm_charlie, "bsm_a": a0, "bsm_b": a1, "cc_ac": cc_alice_charlie, "cc_bc": cc_bob_charlie}

    charlie = topology.Node("charlie", tl, components=components)

    qc_alice_charlie.set_sender(spdc_charlie_1)
    qc_bob_charlie.set_sender(spdc_charlie_2)
    cc_alice_charlie.add_end(charlie)
    cc_bob_charlie.add_end(charlie)

    # add entities to timeline
    tl.entities.append(alice)
    tl.entities.append(bob)
    tl.entities.append(charlie)
    for key in alice.components:
        tl.entities.append(alice.components[key])
    for key in bob.components:
        tl.entities.append(bob.components[key])
    for key in charlie.components:
        tl.entities.append(charlie.components[key])

    # entanglement_swap setup
    es_a = Swap("es_a", tl, role=0)
    es_b = Swap("es_b", tl, role=1)
    es_c = Swap("es_c", tl, role=2)
    es_a.assign_node(alice)
    es_b.assign_node(bob)
    es_c.assign_node(charlie)

    es_a.another_bob = es_b
    es_a.another_charlie = es_c
    es_b.another_alice = es_a
    es_b.another_charlie = es_c
    es_c.another_alice = es_a
    es_c.another_bob = es_b

    alice.protocol = es_a
    bob.protocol = es_b
    charlie.protocol = es_c

    # Run
    process = Process(es_c, "generate_pairs", [100])
    event = Event(0, process)
    tl.schedule(event)

    tl.init()
    tl.run()
