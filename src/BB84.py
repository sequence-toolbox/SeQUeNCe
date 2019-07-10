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
        self.qubit_frequency = 0  # frequency of qubit sending
        self.start_time = 0  # start time of light pulse
        self.node = None
        self.basis_list = []
        self.bits = []
        self.key = 0  # key as int
        self.key_bits = []  # key as list of bits
        self.key_length = 0  # desired key length (from parent)
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

        if message[0] == "begin_photon_pulse":  # (current node is Bob): start to receive photons
            self.qubit_frequency = int(message[1])
            self.light_time = int(message[2])
            self.start_time = self.timeline.now()

            # generate basis list
            bases = [[0, 90], [45, 135]]
            self.basis_list = numpy.random.choice(bases, self.light_time * self.qubit_frequency)

            # schedule changes for BeamSplitter Basis
            for i in range(len(self.basis_list)):
                time = (i / self.qubit_frequency) * (10 ** 12)
                process = Process(self.node.components["detector"], "set_basis", self.basis_list[i])
                event = Event(self.timeline.now() + time, process)
                self.timeline.schedule(event)

            # clear detector photon times to restart measurement
            self.node.components["detector"].clear_detectors()

        elif message[0] == "end_photon_pulse":  # (current node is Bob): done receiving photons
            detection_times = self.node.components["detector"].get_photon_times()
            self.bits = [-1] * (self.light_time * self.qubit_frequency)  # -1 used for invalid bits

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = int(((time - self.start_time) * 10 ** -12) * self.qubit_frequency)
                self.bits[index] = 0

            for time in detection_times[1]:  # detection times for |1> detector
                index = int(((time - self.start_time) * 10 ** -12) * self.qubit_frequency)
                if self.bits[index] == 0:
                    self.bits[index] = -1
                else:
                    self.bits[index] = 1

            self.node.send_message("received_qubits")

        elif message[0] == "received_qubits":  # (Current node is Alice): can send basis
            self.node.send_message("basis_list {}".format(self.basis_list))

        elif message[0] == "basis_list":  # (Current node is Bob): compare bases
            # parse alice basis list
            # NOTE: basis measurements are adjacent but not yet collapsed into a list
            basis_states = []
            for state in message[1:]:
                basis_states.append(int(re.sub("[],[]", "", state)))

            # collapse adjacent basis_states into single basis
            basis_list_alice = []
            basis = []
            count = 0
            while count <= len(basis_states) - 1:
                if count % 2:
                    basis.append(basis_states[count])
                    basis_list_alice.append(basis)
                    basis = []
                else:
                    basis.append(basis_states[count])

            # compare own basis with basis message and create list of matching indices
            indices = []
            for i in range(len(self.basis_list)):
                if self.bits[i] != -1 and self.basis_list[i] == basis_list_alice[i]:
                    indices.append(i)
                    self.key_bits.append(self.bits[i])

            # send to Alice list of matching indices
            self.node.send_message("matching indices {}".format(indices))

        elif message[0] == "matching_indices":  # (Current node is Alice): create key from matching indices
            # parse matching indices
            indices = []
            for val in message[1:]:
                indices.append(int(re.sub("[],[]", "", val)))

            # set key equal to bits at received indices
            for i in indices:
                self.key_bits.append(self.bits[i])

            # check if key long enough. If it is, truncate if necessary and call cascade
            if len(self.key_bits) >= self.key_length:
                del self.key_bits[self.key_length:]
                del self.another.key_bits[self.key_length:]
                self.set_key()  # convert from binary list to int
                self.parent.get_key_from_BB84(self.key)  # call parent
                self.another.set_key()
                self.another.parent.get_key_from_BB84(self.another.key)
            else:
                self.generate_key(self.key_length)

    def generate_key(self, length):
        self.key_length = length
        self.qubit_frequency = self.node.components["lightsource"].frequency
        num_pulses = self.node.components["lightsource"].frequency * self.light_time

        bases = [[0, 90], [45, 135]]
        self.basis_list = numpy.random.choice(bases, num_pulses)  # list of random bases for 1 second
        self.bits = numpy.random.choice([0, 1], num_pulses)  # list of random bits for 1 second

        # send message that photon pulse is beginning, then send bits, then send message that pulse is ending
        self.node.send_message("begin_photon_pulse {} {}".format(self.qubit_frequency, self.light_time))

        self.node.send_photons(self.basis_list, self.bits, "lightsource")

        process = Process(self.node, "send_message", ["end_photon_pulse"])
        event = Event(self.timeline.now() + self.light_time * (10 ** 12), process)
        self.timeline.schedule(event)

        # call to get_key_from_BB84 is handled in received_message (after processing is done)

    def set_key(self):
        self.key = int("".join(str(x) for x in self.key_bits), 2)  # convert from binary list to int
