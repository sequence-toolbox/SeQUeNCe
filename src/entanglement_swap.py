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
        self.bit_list = []
        self.node = None
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
        # emit photons at both sources
        state = [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]
        num_photons = self.light_time * self.qubit_frequency
        self.node.send_photons(state, num_photons, "spdc_a")
        self.node.send_photons(state, num_photons, "spdc_b")

    def end_photon_pulse(self):
        # get indices of detection events
        bits = self.node.get_bits(self.light_time, self.start_time, self.qubit_frequency, "detector")
        self.bit_list = bits
        indices = [i for i, b in enumerate(bits) if b != -1]

        # send indices to Charlie
        message = "received_photons {} {}".format(self.role, indices)
        self.node.send_message(message)

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "begin_entanglement_swap":
            # set params
            self.qubit_frequency = float(message[1])
            self.light_time = float(message[2])
            self.start_time = int(message[3])

            # schedule end_photon_pulse()
            process = Process(self, "end_photon_pulse", [])
            event = Event(self.start_time + int(round(self.light_time * 1e12)), process)
            self.timeline.schedule(event)

            # clear detector photon times to restart measurement
            process = Process(self.node.components["detector"], "clear_detectors", [])
            event = Event(int(self.start_time), process)
            self.timeline.schedule(event)

        if message[0] == "received_photons":
            # determine if from Alice or Bob
            # store indices
            # if received both, send photons to BSM and discard rest of memory
            # get bsm result and send to Bob for correction
            pass

        if message[0] == "bsm_results":
            # correct results
            # compare with Alice?
            pass

    def start_protocol(self):
        # set start time
        self.start_time = self.timeline.now() + int(max(round(self.another_alice.classical_delay),
                                                        round(self.another_bob.classical_delay)))

        # notify Alice and Bob that we are starting entanglement swap
        message = "begin_entanglement_swap {} {} {}".format(self.qubit_frequency, self.light_time, self.start_time)
        self.node.send_message(message, "cc_ac")  # send to Alice
        self.node.send_message(message, "cc_bc")  # send to Bob

        # schedule start for begin_photon_pulse

    def generate_pairs(self, sample_size):
        # assert that start_protocol is called from Charlie (middle node)
        assert self.role == 2

        self.another_alice.sample_size = sample_size
        self.another_bob.sample_size = sample_size

        # set qubit frequency
        lightsource_a = self.node.components["spdc_a"]
        lightsource_b = self.node.components["spdc_b"]
        assert lightsource_a.frequency == lightsource_b.frequency
        self.qubit_frequency = lightsource_a.frequency

        # set light_time
        mean_photon_num = min(lightsource_a.mean_photon_num, lightsource_b.mean_photon_num)
        self.light_time = sample_size / (self.qubit_frequency * mean_photon_num)

        self.start_protocol()


if __name__ == "__main__":
    tl = Timeline()

    # Channels
    qc_alice_charlie = topology.QuantumChannel("qc_ac", tl)
    qc_bob_charlie = topology.QuantumChannel("qc_bc", tl)
    cc_alice_charlie = topology.ClassicalChannel("cc_ac", tl)
    cc_bob_charlie = topology.ClassicalChannel("cc_bc", tl)

    # Alice
    spdc_alice = topology.SPDCSource("alice.ls", tl)
    bsm_alice = topology.BSM("alice.bsm", tl)
    detector_alice = topology.QSDetector("alice.qsd", tl)
    alice = topology.Node("alice", tl)

    # Bob
    spdc_bob = topology.SPDCSource("bob.ls", tl)
    bsm_bob = topology.BSM("bob.bsm", tl)
    detector_bob = topology.QSDetector("bob.qsd", tl)
    bob = topology.Node("bob", tl)

    # Charlie
    spdc_charlie_1 = topology.SPDCSource("charlie.ls_1", tl)
    spdc_charlie_2 = topology.SPDCSource("charlie.ls_2", tl)
    bsm_charlie = topology.BSM("charlie.bsm", tl)
    mem_charlie_1 = topology.Memory("charlie.mem_1", tl)
    mem_charlie_2 = topology.Memory("charlie.mem_2", tl)
    charlie = topology.Node("charlie", tl)
