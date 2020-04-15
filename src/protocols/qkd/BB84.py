import math

import numpy

from ..message import Message
from ..protocol import *
from ...kernel.event import Event
from ...kernel.process import Process


def pair_bb84_protocols(sender: "BB84", receiver: "BB84") -> None:
    sender.another = receiver
    receiver.another = sender
    sender.role = 0
    receiver.role = 1


class BB84Message(Message):
    def __init__(self, msg_type: str, receiver: str, **kwargs):
        Message.__init__(self, msg_type, receiver)
        self.owner_type = BB84
        if self.msg_type == "begin_photon_pulse":
            self.frequency = kwargs["frequency"]
            self.light_time = kwargs["light_time"]
            self.start_time = kwargs["start_time"]
            self.wavelength = kwargs["wavelength"]
        elif self.msg_type == "received_qubits":
            pass
        elif self.msg_type == "basis_list":
            self.bases = kwargs["bases"]
        elif self.msg_type == "matching_indices":
            self.indices = kwargs["indices"]
        else:
            raise Exception("BB84 generated invalid message type {}".format(msg_type))


class BB84(StackProtocol):
    def __init__(self, own: "QKDNode", name: str, **kwargs):
        if own == None:
            return
        super().__init__(own, name)
        self.role = kwargs.get("role", -1)
        
        self.working = False
        self.ready = True  # (for Alice) not currently processing a generate_key request
        self.light_time = 0  # time to use laser (measured in s)
        self.qubit_frequency = 0  # frequency of qubit sending
        self.start_time = 0  # start time of light pulse
        self.photon_delay = 0  # time delay of photon (including dispersion) (ps)
        self.basis_lists = None
        self.bit_lists = None
        self.key = 0  # key as int
        self.key_bits = None  # key as list of bits
        self.another = None
        self.key_lengths = []  # desired key lengths (from parent)
        self.keys_left_list = []
        self.end_run_times = []

        # metrics
        self.latency = 0  # measured in seconds
        self.last_key_time = 0
        self.throughputs = []  # measured in bits/sec
        self.error_rates = []

    def init(self) -> None:
        pass

    def pop(self, detector_index: int, time: int) -> None:
        print(detector_index, time)
        assert 0

    def push(self, length: int, key_num: int, run_time=math.inf) -> None:
        if self.role != 0:
            raise AssertionError("generate key must be called from Alice")

        self.key_lengths.append(length)
        self.another.key_lengths.append(length)
        self.keys_left_list.append(key_num)
        end_run_time = run_time + self.own.timeline.now()
        self.end_run_times.append(end_run_time)
        self.another.end_run_times.append(end_run_time)

        if self.ready:
            self.ready = False
            self.working = True
            self.another.working = True
            self.start_protocol()

    def start_protocol(self) -> None:
        if len(self.key_lengths) > 0:
            # reset buffers for self and another
            self.basis_lists = []
            self.another.basis_lists = []
            self.bit_lists = []
            self.another.bit_lists = []
            self.key_bits = []
            self.another.key_bits = []
            self.latency = 0
            self.another.latency = 0

            self.working = True
            self.another.working = True

            self.qubit_frequency = self.own.lightsource.frequency

            # calculate light time based on key length
            self.light_time = self.key_lengths[0] / (self.qubit_frequency * self.own.lightsource.mean_photon_num)

            # send message that photon pulse is beginning, then send bits
            self.start_time = int(self.own.timeline.now()) + round(self.own.cchannels[self.another.own.name].delay)
            message = BB84Message("begin_photon_pulse", self.another.name, 
                                  frequency=self.qubit_frequency, light_time=self.light_time,
                                  start_time=self.start_time, wavelength=self.own.lightsource.wavelength)
            self.own.send_message(self.another.own.name, message)

            process = Process(self, "begin_photon_pulse", [])
            event = Event(self.start_time, process)
            self.own.timeline.schedule(event)

            self.last_key_time = self.own.timeline.now()
        else:
            self.ready = True

    def begin_photon_pulse(self) -> None:
        if self.working and self.own.timeline.now() < self.end_run_times[0]:
            # generate basis/bit list
            num_pulses = round(self.light_time * self.qubit_frequency)
            basis_list = numpy.random.choice([0, 1], num_pulses)
            bit_list = numpy.random.choice([0, 1], num_pulses)

            # control hardware
            lightsource = self.own.lightsource
            encoding_type = lightsource.encoding_type
            state_list = []
            for i, bit in enumerate(bit_list):
                state = (encoding_type["bases"][basis_list[i]])[bit]
                state_list.append(state)
            lightsource.emit(state_list, self.another.own.name)

            self.basis_lists.append(basis_list)
            self.bit_lists.append(bit_list)

            # schedule another
            self.start_time = self.own.timeline.now()
            process = Process(self, "begin_photon_pulse", [])
            event = Event(self.start_time + int(round(self.light_time * 1e12)), process)
            self.own.timeline.schedule(event)
        else:
            self.working = False
            self.another.working = False

            self.key_lengths.pop(0)
            self.keys_left_list.pop(0)
            self.end_run_times.pop(0)
            self.another.key_lengths.pop(0)
            self.another.end_run_times.pop(0)

            # wait for quantum channel to clear of photons, then start protocol
            time = self.own.timeline.now() + self.own.qchannels[self.another.own.name].delay + 1
            process = Process(self, "start_protocol", [])
            event = Event(time, process)
            self.own.timeline.schedule(event)

    def set_measure_basis_list(self) -> None:
        num_pulses = int(self.light_time * self.qubit_frequency)
        basis_list = numpy.random.choice([0, 1], num_pulses)
        self.basis_lists.append(basis_list)
        self.own.qsdetector.set_basis_list(basis_list, self.start_time, self.qubit_frequency)

    def end_photon_pulse(self) -> None:
        if self.working and self.own.timeline.now() < self.end_run_times[0]:
            # get bits
            self.bit_lists.append(self.own.get_bits(self.light_time, self.start_time, self.qubit_frequency))
            self.start_time = self.own.timeline.now()
            # set bases for measurement
            self.set_measure_basis_list()

            # schedule another if necessary
            if self.own.timeline.now() + self.light_time * 1e12 - 1 < self.end_run_times[0]:
                # schedule another
                process = Process(self, "end_photon_pulse", [])
                event = Event(self.start_time + int(round(self.light_time * 1e12) - 1), process)
                self.own.timeline.schedule(event)

            # send message that we got photons
            message = BB84Message("received_qubits", self.another.name)
            self.own.send_message(self.another.own.name, message)

    def received_message(self, src: str, msg: "Message") -> None:
        if self.working and self.own.timeline.now() < self.end_run_times[0]:
            if msg.msg_type == "begin_photon_pulse":  # (current node is Bob): start to receive photons
                self.qubit_frequency = msg.frequency
                self.light_time = msg.light_time

                # unused dispersion calculations
                # wavelength = int(message[4])
                # qchannel = self.node.components["qchannel"]
                # self.photon_delay = self.quantum_delay +\
                #                     int(round(qchannel.chromatic_dispersion * wavelength * qchannel.distance * 1e-3))
                self.start_time = int(msg.start_time) + self.own.qchannels[src].delay

                # generate and set basis list
                self.set_measure_basis_list()

                # schedule end_photon_pulse()
                process = Process(self, "end_photon_pulse", [])
                event = Event(self.start_time + round(self.light_time * 1e12) - 1, process)
                self.own.timeline.schedule(event)

            elif msg.msg_type == "received_qubits":  # (Current node is Alice): can send basis
                bases = self.basis_lists.pop(0)
                message = BB84Message("basis_list", self.another.name, bases=bases)
                self.own.send_message(self.another.own.name, message)

            elif msg.msg_type == "basis_list":  # (Current node is Bob): compare bases
                # parse alice basis list
                basis_list_alice = msg.bases

                # compare own basis with basis message and create list of matching indices
                indices = []
                basis_list = self.basis_lists.pop(0)
                bits = self.bit_lists.pop(0)
                for i, b in enumerate(basis_list_alice):
                    if bits[i] != -1 and basis_list[i] == b:
                        indices.append(i)
                        self.key_bits.append(bits[i])

                # send to Alice list of matching indices
                message = BB84Message("matching_indices", self.another.name, indices=indices)
                self.own.send_message(self.another.own.name, message)

            elif msg.msg_type == "matching_indices":  # (Current node is Alice): create key from matching indices
                # parse matching indices
                indices = msg.indices

                bits = self.bit_lists.pop(0)

                # set key equal to bits at received indices
                for i in indices:
                    self.key_bits.append(bits[i])

                # check if key long enough. If it is, truncate if necessary and call cascade
                if len(self.key_bits) >= self.key_lengths[0]:
                    throughput = self.key_lengths[0] * 1e12 / (self.own.timeline.now() - self.last_key_time)

                    while len(self.key_bits) >= self.key_lengths[0] and self.keys_left_list[0] > 0:
                        self.set_key()  # convert from binary list to int
                        self._pop(msg=self.key)
                        self.another.set_key()
                        self.another._pop(msg=self.another.key)

                        # for metrics
                        if self.latency == 0:
                            self.latency = (self.own.timeline.now() - self.last_key_time) * 1e-12

                        self.throughputs.append(throughput)

                        key_diff = self.key ^ self.another.key
                        num_errors = 0
                        while key_diff:
                            key_diff &= key_diff - 1
                            num_errors += 1
                        self.error_rates.append(num_errors / self.key_lengths[0])

                        self.keys_left_list[0] -= 1

                    self.last_key_time = self.own.timeline.now()

                # check if we're done
                if self.keys_left_list[0] < 1:
                    self.working = False
                    self.another.working = False

    def set_key(self):
        key_bits = self.key_bits[0:self.key_lengths[0]]
        del self.key_bits[0:self.key_lengths[0]]
        self.key = int("".join(str(x) for x in key_bits), 2)  # convert from binary list to int

