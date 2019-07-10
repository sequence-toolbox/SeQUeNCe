import numpy
import re

from process import Process
from entity import Entity
from event import Event


class BB84(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", None)
        self.light_time = kwargs.get("light_time", 1)  # time to use laser (measured in s)
        self.bit_frequency = 0
        self.start_time = 0
        self.node = None
        self.basis_list = []
        self.bits = []
        self.key = []
        self.key_length = 0
        self.parent = None
        self.another = None

    def init(self):
        pass

    def assign_node(self, node_name):
        self.node = self.timeline.entities[node_name]

    def add_parent(self, parent_name):
        self.parent = self.timeline.entities[parent_name]

    def del_parent(self):
        self.parent = None

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "begin_photon_pulse":  # Bob will start to receive photons
            self.bit_frequency = int(message[1])
            self.light_time = int(message[2])
            self.start_time = self.timeline.now()

            # generate basis list
            bases = [[0, 90], [45, 135]]
            self.basis_list = numpy.random.choice(bases, self.light_time * self.bit_frequency)

            # schedule changes for BeamSplitter Basis
            for i in range(len(self.basis_list)):
                time = (i / self.bit_frequency) * (10 ** 12)
                process = Process(self.node.components["detector"], "set_basis", self.basis_list[i])
                event = Event(self.timeline.now() + time, process)
                self.timeline.schedule(event)

            self.node.components["detector"].clear_detectors()
            pass

        elif message[0] == "end_photon_pulse":  # Bob done receiving photons
            detection_times = self.node.components["detector"].get_photon_times()
            self.bits = [-1] * (self.light_time * self.bit_frequency)  # -1 used for invalid bits

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = int(((time - self.start_time) * 10 ** -12) * self.bit_frequency)
                self.bits[index] = 0

            for time in detection_times[1]:
                index = int(((time - self.start_time) * 10 ** -12) * self.bit_frequency)
                if self.bits[index] == 0:
                    self.bits[index] = -1
                else:
                    self.bits[index] = 1

            self.node.send_message("received_qubits")

        elif message[0] == "received_qubits":  # Alice can send basis
            self.node.send_message("basis_list {}".format(self.basis_list))

        elif message[0] == "basis_list":  # Bob will compare bases
            # parse alice basis list
            # compare own basis with basis message
            # create list of matching indices
            # set key equal to bits with matching bases
            # send to Alice list of matching indices
            pass

        elif message[0] == "matching_indices":  # Alice will create own version of key
            # parse matching indices
            indices = []
            for val in message[1:]:
                indices.append(int(re.sub("[],[]", "", val)))

            # set key equal to bits at received indices
            for i in indices:
                self.key.append(self.bits[i])

            # check if key long enough. If it is, truncate if necessary and call cascade
            if len(self.key) >= self.key_length:
                key = int("".join(str(x) for x in self.key), 2)  # convert from binary list to int
                self.parent.get_key_from_BB84(key)
                self.another.parent.get_key_from_BB84(key)
            else:
                self.generate_key(self.key_length)

    def generate_key(self, length):
        self.key_length = length
        frequency = self.node.components["lightsource"].frequency
        num_pulses = self.node.components["lightsource"].frequency * self.light_time

        bases = [[0, 90], [45, 135]]
        self.basis_list = numpy.random.choice(bases, num_pulses)  # list of random bases for 1 second
        self.bits = numpy.random.choice([0, 1], num_pulses)  # list of random bits for 1 second

        # send message that photon pulse is beginning, then send bits, then send message that pulse is ending
        self.node.send_message("begin_photon_pulse {} {}".format(frequency, self.light_time))
        self.node.send_photons(self.basis_list, self.bits, "lightsource")
        process = Process(self.node, "send_message", ["end_photon_pulse"])
        event = Event(self.timeline.now() + self.light_time * (10 ** 12), process)
        self.timeline.schedule(event)
