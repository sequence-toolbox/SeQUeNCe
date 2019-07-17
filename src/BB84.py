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
        self.role = kwargs.get("role", -1)
        self.encoding_type = kwargs.get("encoding_type")
        self.working = False
        self.light_time = 0  # time to use laser (measured in s)
        self.qubit_frequency = 0  # frequency of qubit sending
        self.start_time = 0  # start time of light pulse
        self.classical_delay = 0  # time delay of classical communication (ps)
        self.quantum_delay = 0  # time delay of quantum communication (ps)
        self.basis_lists = []
        self.bit_lists = []
        self.key = 0  # key as int
        self.key_bits = []  # key as list of bits
        self.node = None
        self.parent = None
        self.another = None
        self.key_length = 0  # desired key length (from parent)
        self.keys_left = 0
        self.end_run_time = 0

        self.bases = []
        if self.encoding_type == 0:
            self.bases = [[[complex(1), complex(0)], [complex(0), complex(1)]],
                          [[complex(math.sqrt(2)), complex(math.sqrt(2))], [complex(-math.sqrt(2)), complex(math.sqrt(2))]]]
        else:
            raise SyntaxError("encoding scheme not specified properly")

    def init(self):
        pass

    def assign_node(self, node):
        self.node = node
        cchannel = node.components["cchannel"]
        qchannel = node.components["qchannel"]
        self.classical_delay = cchannel.delay
        self.quantum_delay = int(round(qchannel.distance / qchannel.light_speed))

    def add_parent(self, parent):
        self.parent = parent

    def del_parent(self):
        self.parent = None

    def set_bases(self):
        # generate basis list
        num_pulses = int(round(self.light_time * self.qubit_frequency))
        basis_list = [[]] * num_pulses
        for i in range(num_pulses):
            basis_list[i] = self.bases[numpy.random.choice([0, 1])]

        self.basis_lists.append(basis_list)

        # schedule changes for BeamSplitter Basis
        basis_start_time = self.start_time - 1e12 / (2 * self.qubit_frequency)
        for i in range(len(basis_list)):
            time = (i * 1e12) / self.qubit_frequency
            process = Process(self.node.components["detector"], "set_basis", [basis_list[i]])
            event = Event(int(round(basis_start_time + time)), process)
            self.timeline.schedule(event)

    def begin_photon_pulse(self):
        if self.working:
            # generate basis list
            num_pulses = int(round(self.light_time * self.qubit_frequency))
            basis_list = [[]] * num_pulses
            for i in range(num_pulses):
                basis_list[i] = self.bases[numpy.random.choice([0, 1])]

            # generate bit list
            bit_list = numpy.random.choice([0, 1], num_pulses)

            # emit photons
            self.node.send_photons(basis_list, bit_list, "lightsource")

            self.basis_lists.append(basis_list)
            self.bit_lists.append(bit_list)

            # schedule another if necessary
            if self.timeline.now() + self.light_time * 1e12 < self.end_run_time:
                self.start_time = self.timeline.now()
                process = Process(self, "begin_photon_pulse", [])
                event = Event(self.start_time + int(round(self.light_time * 1e12)), process)
                self.timeline.schedule(event)

    def end_photon_pulse(self):
        if self.working:
            detection_times = self.node.components["detector"].get_photon_times()
            bits = [-1] * int(round(self.light_time * self.qubit_frequency))  # -1 used for invalid bits

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = int(round((time - self.start_time) * self.qubit_frequency * 1e-12))
                if index < len(bits):
                    bits[index] = 0

            for time in detection_times[1]:  # detection times for |1> detector
                index = int(round((time - self.start_time) * self.qubit_frequency * 1e-12))
                if index < len(bits):
                    if bits[index] == 0:
                        bits[index] = -1
                    else:
                        bits[index] = 1

            self.bit_lists.append(bits)

            # clear detector photon times to restart measurement
            self.node.components["detector"].clear_detectors()

            # schedule another if necessary
            if self.timeline.now() + self.light_time * 1e12 < self.end_run_time:
                self.start_time = self.timeline.now()

                # set beamsplitter bases
                self.set_bases()

                # schedule another
                process = Process(self, "end_photon_pulse", [])
                event = Event(self.start_time + int(round(self.light_time * 1e12)), process)
                self.timeline.schedule(event)

            # send message that we got photons
            self.node.send_message("received_qubits")

    def received_message(self):
        if self.working:
            message = self.node.message.split(" ")

            if message[0] == "begin_photon_pulse":  # (current node is Bob): start to receive photons
                self.qubit_frequency = float(message[1])
                self.light_time = float(message[2])
                self.start_time = int(message[3]) + self.quantum_delay

                # generate basis list and set beamsplitter
                self.set_bases()

                # schedule end_photon_pulse()
                process = Process(self, "end_photon_pulse", [])
                event = Event(self.start_time + int(round(self.light_time * 1e12)), process)
                self.timeline.schedule(event)

                # clear detector photon times to restart measurement
                process = Process(self.node.components["detector"], "clear_detectors", [])
                event = Event(int(self.start_time), process)
                self.timeline.schedule(event)

            elif message[0] == "received_qubits":  # (Current node is Alice): can send basis
                bases = self.basis_lists.pop(0)
                self.node.send_message("basis_list {}".format(bases))

            elif message[0] == "basis_list":  # (Current node is Bob): compare bases
                # parse alice basis list
                # NOTE: basis measurements are adjacent but not yet collapsed into a list
                basis_coefficients = []
                for state in message[1:]:
                    basis_coefficients.append(complex(re.sub("[],[()]", "", state)))

                # collapse adjacent basis coefficients into single basis state
                basis_states = []
                state = []
                for i, c in enumerate(basis_coefficients):
                    state.append(c)
                    if i % 2:
                        basis_states.append(state)
                        state = []

                # collapse adjacent basis_states into single basis
                basis_list_alice = []
                basis = []
                for i, s in enumerate(basis_states):
                    basis.append(s)
                    if i % 2:
                        basis_list_alice.append(basis)
                        basis = []

                # compare own basis with basis message and create list of matching indices
                indices = []
                basis_list = self.basis_lists.pop(0)
                bits = self.bit_lists.pop(0)
                for i in range(len(basis_list)):
                    if bits[i] != -1 and basis_list[i] == basis_list_alice[i]:
                        indices.append(i)
                        self.key_bits.append(bits[i])

                # send to Alice list of matching indices
                self.node.send_message("matching_indices {}".format(indices))

            elif message[0] == "matching_indices":  # (Current node is Alice): create key from matching indices
                # parse matching indices
                indices = []
                if message[1] != "[]":  # no matching indices
                    for val in message[1:]:
                        indices.append(int(re.sub("[],[]", "", val)))

                bits = self.bit_lists.pop(0)

                # set key equal to bits at received indices
                for i in indices:
                    self.key_bits.append(bits[i])

                # check if key long enough. If it is, truncate if necessary and call cascade
                while len(self.key_bits) >= self.key_length and self.keys_left > 0:
                    self.set_key()  # convert from binary list to int
                    self.parent.get_key_from_BB84(self.key)  # call parent
                    self.another.set_key()
                    self.another.parent.get_key_from_BB84(self.another.key)

                    # for testing
                    key_diff = self.key ^ self.another.key
                    num_errors = bin(key_diff).count("1")
                    print("bit error rate: {}%".format(num_errors / self.key_length * 100))

                    self.keys_left -= 1

                # check if we're done
                if self.keys_left < 1 or self.timeline.now() >= self.end_run_time:
                    self.working = False
                    self.another.working = False

    def generate_key(self, length, key_num=1, run_time=math.inf):
        if self.role != 0:
            raise AssertionError("generate key must be called from Alice")

        self.key_length = length
        self.another.key_length = length
        self.keys_left = key_num
        self.end_run_time = run_time + self.timeline.now()
        self.another.end_run_time = self.end_run_time

        self.working = True
        self.another.working = True

        light_source = self.node.components["lightsource"]
        self.qubit_frequency = light_source.frequency

        # calculate light time based on delay
        # self.light_time = self.classical_delay * 2 * 1e-12
        self.light_time = self.key_length / (self.qubit_frequency * light_source.mean_photon_num)

        # send message that photon pulse is beginning, then send bits
        self.start_time = int(self.timeline.now()) + int(round(self.classical_delay))
        self.node.send_message("begin_photon_pulse {} {} {}"
                               .format(self.qubit_frequency, self.light_time, self.start_time))

        process = Process(self, "begin_photon_pulse", [])
        event = Event(self.start_time, process)
        self.timeline.schedule(event)

        # call to get_key_from_BB84 is handled in received_message (after processing is done)

    def set_key(self):
        key_bits = self.key_bits[0:self.key_length - 1]
        del self.key_bits[0:self.key_length - 1]
        self.key = int("".join(str(x) for x in key_bits), 2)  # convert from binary list to int


if __name__ == "__main__":
    # dummy parent class to test BB84 functionality
    class Parent:
        def __init__(self, keysize, role):
            self.keysize = keysize
            self.role = role
            self.child = None
            self.key = 0

        def run(self):
            self.child.generate_key(self.keysize, 10)

        def get_key_from_BB84(self, key):
            print("key for " + self.role + ":\t{:0{}b}".format(key, self.keysize))
            self.key = key

    tl = timeline.Timeline(1e9)  # stop time is 1 ms

    qc = topology.QuantumChannel("qc", tl, distance=10e3, polarization_fidelity=0.99)
    cc = topology.ClassicalChannel("cc", tl, distance=10e3)

    # Alice
    ls = topology.LightSource("alice.lightsource", tl,
                              frequency=80e6, mean_photon_num=0.1, direct_receiver=qc)
    components = {"lightsource": ls, "cchannel": cc, "qchannel": qc}

    alice = topology.Node("alice", tl, components=components)
    qc.set_sender(ls)
    cc.add_end(alice)

    # Bob
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
    for key in alice.components:
        tl.entities.append(alice.components[key])
    for key in bob.components:
        tl.entities.append(bob.components[key])

    # BB84
    bba = BB84("bba", tl, role=0, encoding_type=0)
    bbb = BB84("bbb", tl, role=1, encoding_type=0)
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

    tl.init()
    tl.run()
