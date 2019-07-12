import numpy
import re
import math

from process import Process
from entity import Entity
from event import Event
# use for testing
import topology
import timeline


class BB84(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", None)
        self.light_time = 0  # time to use laser (measured in s)
        self.qubit_frequency = 0  # frequency of qubit sending
        self.start_time = 0  # start time of light pulse
        self.node = None
        self.classical_delay = 0  # time delay of classical communication (ps)
        self.quantum_delay = 0  # time delay of quantum communication (ps)
        self.basis_list = []
        self.bits = []
        self.key = 0  # key as int
        self.key_bits = []  # key as list of bits
        self.key_length = 0  # desired key length (from parent)
        self.parent = None
        self.another = None
        self.keys_left = 0
        self.end_run_time = 0

    def init(self):
        pass

    def assign_node(self, node):
        self.node = node
        cchannel = node.components["cchannel"]
        qchannel = node.components["qchannel"]
        self.classical_delay = cchannel.delay
        self.quantum_delay = qchannel.distance / qchannel.light_speed

    def add_parent(self, parent):
        self.parent = parent

    def del_parent(self):
        self.parent = None

    def end_photon_pulse(self):
        detection_times = self.node.components["detector"].get_photon_times()
        self.bits = [-1] * int(self.light_time * self.qubit_frequency)  # -1 used for invalid bits

        # determine indices from detection times and record bits
        for time in detection_times[0]:  # detection times for |0> detector
            index = int(round((time - self.start_time) * self.qubit_frequency * (10 ** -12)))
            self.bits[index] = 0

        for time in detection_times[1]:  # detection times for |1> detector
            index = int((time - self.start_time) * self.qubit_frequency * (10 ** -12))
            if self.bits[index] == 0:
                self.bits[index] = -1
            else:
                self.bits[index] = 1

        self.node.send_message("received_qubits")

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "begin_photon_pulse":  # (current node is Bob): start to receive photons
            self.qubit_frequency = float(message[1])
            self.light_time = float(message[2])
            self.start_time = int(message[3]) + int(round(self.quantum_delay))  # self.timeline.now()

            # generate basis list
            num_pulses = int(self.light_time * self.qubit_frequency)
            bases = [[0, 90], [45, 135]]
            self.basis_list = [[]] * num_pulses
            for i in range(num_pulses):
                self.basis_list[i] = bases[numpy.random.choice([0, 1])]

            # schedule changes for BeamSplitter Basis
            for i in range(len(self.basis_list)):
                time = (i / self.qubit_frequency) * (10 ** 12)
                process = Process(self.node.components["detector"], "set_basis", [self.basis_list[i]])
                event = Event(self.start_time + time, process)
                self.timeline.schedule(event)

            # schedule end_photon_pulse()
            process = Process(self, "end_photon_pulse", [])
            event = Event(self.start_time + self.light_time * (10 ** 12), process)
            self.timeline.schedule(event)

            # clear detector photon times to restart measurement
            self.node.components["detector"].clear_detectors()

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
                count += 1

            # compare own basis with basis message and create list of matching indices
            indices = []
            for i in range(len(self.basis_list)):
                if self.bits[i] != -1 and self.basis_list[i] == basis_list_alice[i]:
                    indices.append(i)
                    self.key_bits.append(self.bits[i])

            # send to Alice list of matching indices
            self.node.send_message("matching_indices {}".format(indices))

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

                self.keys_left -= 1
                # check if we've made enough keys or run out of time
                if self.keys_left > 0 and self.end_run_time > self.timeline.now():
                    self.key_bits = 0
                    self.key = 0
                    self.key_bits = []
                    self.another.key_bits = []
                    process = Process(self, "generate_key", [self.key_length,
                                                             self.keys_left,
                                                             self.end_run_time - self.timeline.now()])
                    event = Event(self.timeline.now(), process)
                    self.timeline.schedule(event)

            else:
                process = Process(self, "generate_key", [self.key_length,
                                                         self.keys_left,
                                                         self.end_run_time - self.timeline.now()])
                event = Event(self.timeline.now(), process)
                self.timeline.schedule(event)

    def generate_key(self, length, key_num=1, run_time=math.inf):
        self.key_length = length
        self.keys_left = key_num
        self.end_run_time = run_time + self.timeline.now()

        # calculate number of pulses based on number of bits to generate
        num_pulses = int(length * (1 / self.node.components["lightsource"].mean_photon_num))
        self.light_time = num_pulses / self.node.components["lightsource"].frequency

        self.qubit_frequency = self.node.components["lightsource"].frequency

        # list of random bases for 1 second
        bases = [[0, 90], [45, 135]]
        self.basis_list = [[]] * num_pulses
        for i in range(num_pulses):
            self.basis_list[i] = bases[numpy.random.choice([0, 1])]

        self.bits = numpy.random.choice([0, 1], num_pulses)  # list of random bits for 1 second

        # send message that photon pulse is beginning, then send bits, then send message that pulse is ending
        self.start_time = int(self.timeline.now()) + int(round(self.classical_delay))
        self.node.send_message("begin_photon_pulse {} {} {}"
                               .format(self.qubit_frequency, self.light_time, self.start_time))

        process = Process(self.node, "send_photons", [self.basis_list, self.bits, "lightsource"])
        event = Event(self.start_time, process)
        self.timeline.schedule(event)
        # self.node.send_photons(self.basis_list, self.bits, "lightsource")

        # call to get_key_from_BB84 is handled in received_message (after processing is done)

    def set_key(self):
        self.key = int("".join(str(x) for x in self.key_bits), 2)  # convert from binary list to int


if __name__ == "__main__":
    # dummy parent class to test BB84 functionality
    class Parent:
        def __init__(self, keysize, role):
            self.keysize = keysize
            self.role = role
            self.child = None
            self.key = 0

        def run(self):
            self.child.generate_key(self.keysize)

        def get_key_from_BB84(self, key):
            print("key for " + self.role + ":\t{:0b}".format(key))
            self.key = key

    tl = timeline.Timeline(10 ** 13)  # stop time is 10 seconds

    qc = topology.QuantumChannel("qc", tl, distance=10000, polarization_fidelity=0.99)
    cc = topology.ClassicalChannel("cc", tl, distance=10000)

    # Alice
    ls = topology.LightSource("alice.lightsource", tl,
                              frequency=80000000, mean_photon_num=0.1, direct_receiver=qc)
    components = {"lightsource": ls, "cchannel": cc, "qchannel": qc}

    alice = topology.Node("alice", tl, components=components)
    qc.set_sender(ls)
    cc.add_end(alice)

    # Bob
    # d_0 = topology.Detector(tl, dark_count=1, time_resolution=1)
    # d_1 = topology.Detector(tl, dark_count=1, time_resolution=1)
    # bs = topology.BeamSplitter(tl)
    detectors = [{"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                 {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10}]
    splitter = {}
    qsd = topology.QSDetector("bob.qsdetector", tl, detectors=detectors, splitter=splitter)
    components = {"detector": qsd, "cchannel": cc, "qchannel": qc}

    bob = topology.Node("bob", tl, components=components)
    qc.set_receiver(qsd)
    cc.add_end(bob)

    tl.entities.append(alice)
    tl.entities.append(bob)

    # BB84
    bba = BB84("bba", tl, role="alice")
    bbb = BB84("bbb", tl, role="bob")
    bba.assign_node(alice)
    bbb.assign_node(bob)
    bba.another = bbb
    bbb.another = bba
    alice.protocol = bba
    bob.protocol = bbb

    # Parent
    pa = Parent(256, "alice")
    pb = Parent(256, "bob")
    pa.child = bba
    pb.child = bbb
    bba.add_parent(pa)
    bbb.add_parent(pb)

    process = Process(pa, "run", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.run()

    key_diff = pa.key ^ pb.key
    num_errors = bin(key_diff).count("1")
    print("bit error rate: {}%".format(num_errors/pa.keysize * 100))
