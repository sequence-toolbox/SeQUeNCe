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
                self.generate_pair()
                return

            #otherwise, send to BSM
            self.start_time = self.timeline.now()
            self.node.components["bsm_a"].get(photon_alice)
            self.node.components["bsm_b"].get(photon_bob)
            #schedule result measurement after 1 period
            future_time = self.timeline.now() + int((1 / self.frequency) * 1e12)
            process = Process(self, "get_bsm_res", [])
            event = Event(future_time, process)
            self.timeline.schedule(event)

        else:
            self.received_first_pulse = True

    def get_bsm_res(self):
        results = self.node.components["bsm"].get_bsm_res()
        bsm_res = -1
        for res in results:
            if res[0] > self.start_time:
                bsm_res = res[1]
        
        message = "bsm_result {}".format(bsm_res)
        self.node.send_message(message, "cc_a")
        self.node.send_message(message, "cc_b")

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "begin_protocol":
            # current node: Alice or Bob
            mean_photon_num = self.node.components["spdc"].mean_photon_num
            frequency = self.node.components["spdc"].frequency
            num_pulses = 1 / mean_photon_number
            light_time = num_pulses / frequency

            state = [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]
            self.node.send_photons(state, num_pulses, "spdc")

            # send message that we're sending photons
            self.node.send_message("sending_photons {} {}".format(self.timeline.now(), light_time))

        if message[0] == "sending_photons":
            # current node: Charlie

            # schedule end_photon_pulse
            end_photon_time = int(message[1]) + int(1e12 * float(message[2])) + self.quantum_delay
            process = Process(self, "end_photon_pulse", [])
            event = Event(end_photon_time, process)
            self.timeline.schedule(event)

        if message[0] == "bsm_result":
            pass

    def generate_pair(self):
        # assert that start_protocol is called from Charlie (middle node)
        assert self.role == 2

        self.frequency = min(self.another_alice.node.components["spdc"].frequency, self.another_bob.node.components["spdc"].frequency)

        message = "begin_protocol"
        # send start message to Alice
        self.node.send_message(message, "cc_a")
        # send start message to Bob
        self.node.send_message(message, "cc_b")


# main function for testing
if __name__ == "__main__":
    
    test = DLCZ("test", None)

