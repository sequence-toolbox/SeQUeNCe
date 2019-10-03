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

    def generate_pairs(self, sample_size):
        # assert that start_protocol is called from Alice (middle node)
        assert self.role == 0

        self.sample_size = sample_size
        self.bit_lengths = [0, 0]

        lightsource = self.node.components["spdc"]
        lightsource_bob = self.another_bob.node.components["spdc"]
        assert lightsource.frequency == lightsource_bob.frequency

        self.qubit_frequency = lightsource.frequency
        self.another_bob.qubit_frequency = lightsource.frequency
	self.another_charlie.qubit_frequency = lightsource.frequency

        # set light_time
        mean_photon_num = min(lightsource.mean_photon_num, lightsource_bob.mean_photon_num)
        self.light_time = sample_size / (self.qubit_frequency * mean_photon_num)

        self.start_protocol()

