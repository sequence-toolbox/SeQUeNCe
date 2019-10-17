"""
Network Topology:
(ALICE)===(CHARLIE)===(BOB)

ALICE:
    SPDC Source
    Memory
    Detector

CHARLIE:
    BSM

BOB:
    SPDC Source
    Memory
    Detector
"""
import math
import numpy
import re

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event
from sequence.timeline import Timeline
from sequence import topology


# Protocol
class DLCZ(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", -1)  # Alice, Bob, Charlie are 0, 1, 2, respectively

        self.classical_delay = 0
        self.quantum_delay = 0 
        self.received_first_pulse = False
        self.start_time = 0

        self.parent = None

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

    def end_photon_pulse(self):
        if self.received_first_pulse:
            photon_alice = self.node.components["memory_a"].retrieve_photon()
            photon_bob = self.node.components["memory_b"].retrieve_photon()

            # if we didn't get both photons, restart protocol
            if photon_alice is None or photon_bob is None:
                message = "begin_protocol"
                # send start message to Alice
                self.node.send_message(message, "cc_a")
                # send start message to Bob
                self.node.send_message(message, "cc_b")
            #otherwise, send to BSM
            else:
                self.start_time = self.timeline.now()
                self.node.components["bsm_a"].get(photon_alice)
                self.node.components["bsm_b"].get(photon_bob)
                #schedule result measurement after 1 period
                future_time = self.timeline.now() + int((1 / self.frequency) * 1e12)
                process = Process(self, "get_bsm_res", [])
                event = Event(future_time, process)
                self.timeline.schedule(event)

            self.received_first_pulse = False

        else:
            self.received_first_pulse = True

    def get_bsm_res(self):
        results = self.node.components["bsm"].get_bsm_res()
        print("bsm result at node {}: {}".format(self.role, results))
        bsm_res = -1
        for res in results:
            if res[0] > self.start_time:
                bsm_res = res[1]
       
        if bsm_res == -1:
            message = "begin_protocol"
            # send start message to Alice
            self.node.send_message(message, "cc_a")
            # send start message to Bob
            self.node.send_message(message, "cc_b")
            return
        else:    
            message = "bsm_result {}".format(bsm_res)
            self.node.send_message(message, "cc_a")
            self.node.send_message(message, "cc_b")

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "begin_protocol":
            # current node: Alice or Bob
            mean_photon_num = self.node.components["spdc"].mean_photon_num
            frequency = self.node.components["spdc"].frequency
            num_pulses = int(1 / mean_photon_num)
            light_time = num_pulses / frequency

            state = [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]
            self.node.send_photons(state, num_pulses, "spdc")

            # send message that we're sending photons
            self.node.send_message("sending_photons {} {} {}".format(self.timeline.now(), light_time, self.quantum_delay))

        elif message[0] == "sending_photons":
            # current node: Charlie

            # schedule end_photon_pulse
            end_photon_time = int(message[1]) + int(1e12 * float(message[2])) + int(message[3])
            process = Process(self, "end_photon_pulse", [])
            event = Event(end_photon_time, process)
            self.timeline.schedule(event)

        elif message[0] == "bsm_result":
            # current node: Alice or Bob
            print("Received bsm result {} at node {}".format(message[1], self.role))

    def generate_pair(self):
        # assert that start_protocol is called from Charlie (middle node)
        assert self.role == 2

        self.frequency = min(self.another_alice.components["spdc"].frequency, self.another_bob.components["spdc"].frequency)

        message = "begin_protocol"
        # send start message to Alice
        self.node.send_message(message, "cc_a")
        # send start message to Bob
        self.node.send_message(message, "cc_b")


# main function for testing
if __name__ == "__main__":
    # numpy.random.seed(1)

    tl = Timeline(1e12)
    
    # CHANGE THESE TO CHANGE DISTANCE TO NODE (measured in m)
    alice_distance = 100
    bob_distance = 100

    qc_alice_charlie = topology.QuantumChannel("qc_ac", tl, distance=alice_distance, attenuation=0.0002)
    qc_bob_charlie = topology.QuantumChannel("qc_bc", tl, distance=bob_distance, attenuation=0.0002)
    cc_alice_charlie = topology.ClassicalChannel("cc_ac", tl, distance=alice_distance)
    cc_bob_charlie = topology.ClassicalChannel("cc_bc", tl, distance=bob_distance)

    # Alice
    detectors = [{"efficiency": 1, "dark_count": 100, "time_resolution": 100},
                 None,
                 None]
    interferometer = {}
    switch = {"state": 0}
    detector_alice = topology.QSDetector("alice.qsd", tl, encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer, switch=switch)

    memory_alice = topology.Memory("alice.memory", tl)

    spdc_alice = topology.SPDCSource("alice.ls", tl, frequency=80e6, mean_photon_num=0.045, encoding_type=encoding.time_bin, direct_receiver=qc_alice_charlie,
                                     another_receiver=memory_alice, wavelengths=[1532, 795], phase_error=0)

    components = {"detector": detector_alice, "memory": memory_alice, "spdc": spdc_alice, "qchannel": qc_alice_charlie, "cchannel": cc_alice_charlie}

    alice = topology.Node("alice", tl, components=components)

    qc_alice_charlie.set_sender(spdc_alice)
    cc_alice_charlie.add_end(alice)

    # Bob
    detectors = [{"efficiency": 1, "dark_count": 100, "time_resolution": 100},
                 None,
                 None]
    interferometer = {}
    switch = {"state": 0}
    detector_bob = topology.QSDetector("bob.qsd", tl, encoding_type=encoding.time_bin, detectors=detectors, interferometer=interferometer, switch=switch)

    memory_bob = topology.Memory("bob.memory", tl)

    spdc_bob = topology.SPDCSource("bob.ls", tl, frequency=80e6, mean_photon_num=0.045, encoding_type=encoding.time_bin, direct_receiver=qc_bob_charlie,
                                   another_receiver=memory_bob, wavelengths=[1523, 795], phase_error=0)

    components = {"detector": detector_bob, "memory": memory_bob, "spdc": spdc_bob, "qchannel": qc_bob_charlie, "cchannel": cc_bob_charlie}

    bob = topology.Node("bob", tl, components=components)

    qc_bob_charlie.set_sender(spdc_bob)
    cc_bob_charlie.add_end(bob)

    # Charlie
    mem_charlie_1 = topology.Memory("charlie.mem_1", tl)
    mem_charlie_2 = topology.Memory("charlie.mem_2", tl)

    detectors = [{"efficiency": 1, "dark_count": 100, "time_resolution": 150, "count_rate": 25e6},
                 {"efficiency": 1, "dark_count": 100, "time_resolution": 150, "count_rate": 25e6}]
    bsm_charlie = topology.BSM("charlie.bsm", tl, encoding_type=encoding.time_bin, detectors=detectors, phase_error=0)
    a0 = topology.BSMAdapter(tl, photon_type=0, bsm=bsm_charlie)
    a1 = topology.BSMAdapter(tl, photon_type=1, bsm=bsm_charlie)

    components = {"memory_a": mem_charlie_1, "memory_b": mem_charlie_2, "bsm": bsm_charlie, "bsm_a": a0, "bsm_b": a1,
                  "cc_a": cc_alice_charlie, "cc_b": cc_bob_charlie}

    charlie = topology.Node("charlie", tl, components=components)

    qc_alice_charlie.set_receiver(mem_charlie_1)
    qc_bob_charlie.set_receiver(mem_charlie_2)
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

    # dlcz setup
    dlcz_a = DLCZ("dlcz_a", tl, role=0)
    dlcz_b = DLCZ("dlcz_b", tl, role=1)
    dlcz_c = DLCZ("dlcz_c", tl, role=2)
    dlcz_a.assign_node(alice)
    dlcz_b.assign_node(bob)
    dlcz_c.assign_node(charlie)

    dlcz_a.another_bob = bob
    dlcz_a.another_charlie = charlie
    dlcz_b.another_alice = alice
    dlcz_b.another_charlie = charlie
    dlcz_c.another_alice = alice
    dlcz_c.another_bob = bob

    alice.protocol = dlcz_a
    bob.protocol = dlcz_b
    charlie.protocol = dlcz_c

    # run
    process = Process(dlcz_c, "generate_pair", [])
    event = Event(10, process)
    tl.schedule(event)

    tl.init()
    tl.run()


