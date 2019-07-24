import math
from typing import List, Any

import numpy
import json5
import pandas as pd

import encoding
from process import Process
from entity import Entity
from event import Event

from BB84 import BB84


class TemperatureModel():
    df = pd.DataFrame()

    def read_temperature_file(self,filename):
        self.df = pd.read_csv(filename)
        print (filename,self.df)
        return self.df

    def temperature_from_time(self,time):
        ## TODO
        ## interpolation of time
        temperature = 60
        return temperature


class Photon(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.wavelength = kwargs.get("wavelength", 0)
        self.location = kwargs.get("location", None)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        self.quantum_state = kwargs.get("quantum_state", [complex(1), complex(0)])

    def init(self):
        pass

    def random_noise(self):
        angle = numpy.random.random() * 2 * numpy.pi
        self.quantum_state = [complex(numpy.cos(angle)), complex(numpy.sin(angle))]
        # self.quantum_state += numpy.random.random() * 360  # add random angle, use 360 instead of 2*pi

    def measure(self, basis):
        alpha = numpy.dot(self.quantum_state, basis[0])  # projection onto basis vector
        # alpha = numpy.cos((self.quantum_state - basis[0])/180.0 * numpy.pi)
        if numpy.random.random_sample() < alpha ** 2:
            self.quantum_state = basis[0]
            return 0
        self.quantum_state = basis[1]
        return 1


class OpticalChannel(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.attenuation = kwargs.get("attenuation", 0)
        self.distance = kwargs.get("distance", 0)
        self.temperature = kwargs.get("temperature", 0)
        self.polarization_fidelity = kwargs.get("polarization_fidelity", 1)
        self.light_speed = kwargs.get("light_speed",
                                      3 * 10 ** -4)  # used for photon timing calculations (measured in m/ps)

    def init(self):
        pass

    def set_distance(self, distance):
        self.distance = distance

    def distance_from_time(self, time):
        distance = self.distance
        ## TODO: distance as a function of temperature
        temperature = self.tModel.temperature_from_time(time)

        return distance

    def set_temerature_model(self, filename):
        self.tModel = TemperatureModel()
        self.tModel.read_temperature_file(filename)


class QuantumChannel(OpticalChannel):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline, **kwargs)
        self.sender = None
        self.receiver = None
        self.depo_counter = 0
        self.photon_counter = 0

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

    def get(self, photon):
        # generate chance to lose photon
        loss = self.distance * self.attenuation
        chance_photon_kept = 10 ** (loss / -10)

        # check if photon kept
        if numpy.random.random_sample() < chance_photon_kept:
            self.photon_counter+=1
            # check if random polarization noise applied
            if numpy.random.random_sample() > self.polarization_fidelity:
                photon.random_noise()
                self.depo_counter+=1
            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + int(self.distance / self.light_speed)
            process = Process(self.receiver, "get", [photon])

            event = Event(future_time, process)
            self.timeline.schedule(event)


class ClassicalChannel(OpticalChannel):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline, **kwargs)
        self.ends = []
        self.delay = kwargs.get("delay", (self.distance / self.light_speed))

    def add_end(self, node):
        if node in self.ends:
            Exception("already have endpoint", node)
        if len(self.ends) == 2:
            Exception("channel already has 2 endpoints")

        self.ends.append(node)

    def transmit(self, message, source):
        # get node that's not equal to source
        if source not in self.ends:
            Exception("no endpoint", source)

        receiver = None
        for e in self.ends:
            if e != source:
                receiver = e

        future_time = int(round(self.timeline.now() + self.delay))
        process = Process(receiver, "receive_message", [message])
        event = Event(future_time, process)
        self.timeline.schedule(event)


class LightSource(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.frequency = kwargs.get("frequency", 0)  # measured in Hz
        self.wavelength = kwargs.get("wavelength", 0)  # measured in nm
        self.mean_photon_num = kwargs.get("mean_photon_num", 0)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.photon_counter = 0
        # for BB84
        self.basis_lists = []
        self.basis_list = []
        self.bit_lists = []
        self.bit_list = []
        self.is_on = False
        self.pulse_id = 0

    def init(self):
        pass

    # for BB84
    def emit_photon(self):
        if self.is_on:
            bases = [[0, 90], [45, 135]]
            basis = bases[numpy.random.choice([0, 1])]
            self.basis_list.append(basis)
            bit = numpy.random.choice([0, 1])
            self.bit_list.append(bit)
            state = basis[bit]

            num_photons = numpy.random.poisson(self.mean_photon_num)
            for _ in range(num_photons):
                new_photon = Photon(self.pulse_id, self.timeline,
                                    wavelength=self.wavelength,
                                    location=self.direct_receiver,
                                    encoding_type=self.encoding_type,
                                    quantum_state=state)
                self.direct_receiver.get(new_photon)

                self.photon_counter += 1

            self.pulse_id+=1
            process = Process(self, "emit_photon", [])
            event = Event(self.timeline.now() + 1e12 / self.frequency, process)
            self.timeline.schedule(event)

    # for general use
    def emit(self, state_list):
        time = self.timeline.now()

        for i, state in enumerate(state_list):
            num_photons = numpy.random.poisson(self.mean_photon_num)

            for _ in range(num_photons):
                new_photon = Photon(None, self.timeline,
                                    wavelength=self.wavelength,
                                    location=self.direct_receiver,
                                    encoding_type=self.encoding_type,
                                    quantum_state=state)
                process = Process(self.direct_receiver, "get", [new_photon])
                event = Event(int(round(time)), process)
                self.timeline.schedule(event)

                self.photon_counter += 1

            time += 1e12 / self.frequency

    def turn_on(self):
        self.is_on = True
        self.emit_photon()

    def turn_off(self):
        self.basis_lists.append(self.basis_list)
        self.basis_list = []
        self.bit_lists.append(self.bit_list)
        self.bit_list = []
        self.is_on = False

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver


class QSDetector(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)

        detectors = kwargs.get("detectors", [])
        if (self.encoding_type["name"] == "polarization" and len(detectors) != 2) or\
                (self.encoding_type["name"] == "time_bin" and len(detectors) != 3):
            raise Exception("invalid number of detectors specified")
        self.detectors = []
        for d in detectors:
            detector = Detector(timeline, **d)
            self.detectors.append(detector)

        if self.encoding_type["name"] == "polarization":
            splitter = kwargs.get("splitter")
            self.splitter = BeamSplitter(timeline, **splitter)

        elif self.encoding_type["name"] == "time_bin":
            interferometer = kwargs.get("interferometer")
            self.interferometer = Interferometer(timeline, **interferometer)
            self.interferometer.detectors = self.detectors[1:2]
            switch = kwargs.get("switch")
            self.switch = Switch(timeline, **switch)
            self.switch.receivers = [self.detectors[0], self.interferometer]

        else:
            raise Exception("invalid encoding type for QSDetector " + self.name)

    def init(self):
        for d in self.detectors:
            d.init()

    def get(self, photon):
        if self.encoding_type["name"] == "polarization":
            detector = self.splitter.get(photon)
            if detector == 0 or detector == 1:
                self.detectors[self.splitter.get(photon)].get()

        elif self.encoding_type["name"] == "time_bin":
            self.switch.get(photon)

    def clear_detectors(self):
        for d in self.detectors:
            d.photon_times = []

    def get_photon_times(self):
        times = []
        for d in self.detectors:
            times.append(d.photon_times)
        return times

    def set_basis(self, basis):
        self.splitter.set_basis(basis)


class Detector(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = kwargs.get("efficiency", 1)
        self.dark_count = kwargs.get("dark_count", 0)  # measured in Hz
        self.count_rate = kwargs.get("count_rate", math.inf)  # measured in Hz
        self.time_resolution = kwargs.get("time_resolution", 0)  # measured in ps
        self.photon_times = []
        self.next_detection_time = 0
        self.photon_counter = 0

    def init(self):
        self.add_dark_count()

    def get(self, photon=None):
        self.photon_counter += 1
        now = self.timeline.now()

        if photon and photon.encoding_type["name"] == "time_bin":
            # check if photon is in "late" bin. If it is, detect at late time
            if photon.measure(photon.encoding_type["bases"][0]):
                now += photon.encoding_type["bin_separation"]

        if numpy.random.random_sample() < self.efficiency and now > self.next_detection_time:
            time = int(round(now / self.time_resolution)) * self.time_resolution
            self.photon_times.append(time)
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def add_dark_count(self):
        time_to_next = int(numpy.random.exponential(1 / self.dark_count) * 1e12)  # time to next dark count
        time = time_to_next + self.timeline.now()  # time of next dark count

        process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
        process2 = Process(self, "get", [])
        event1 = Event(time, process1)
        event2 = Event(time, process2)
        self.timeline.schedule(event1)
        self.timeline.schedule(event2)


class BeamSplitter(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)  # Splitter is part of the QSDetector, and does not have its own name
        basis = kwargs.get("basis", [[complex(1), complex(0)], [complex(0), complex(1)]])
        self.fidelity = kwargs.get("fidelity", 1)
        # for BB84
        self.start_time = 0
        self.frequency = 0
        self.basis_list = [basis]  # default value

    def init(self):
        pass

    # # for general use
    # def transmit_general(self, photon):
    #     if numpy.random.random_sample() < self.fidelity:
    #         return photon.measure(self.basis)
    #     else:
    #         return -1

    # for BB84
    # TODO: determine if protocol is BB84
    def get(self, photon):
        if numpy.random.random_sample() < self.fidelity:
            index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
            if 0 <= index < len(self.basis_list):
                return photon.measure(self.basis_list[index])
            else:
                return photon.measure(self.basis_list[0])
        else:
            return -1

    def set_basis(self, basis):
        self.basis_list = [basis]


class Interferometer(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)
        self.path_difference = ("path_difference", 0)  # time difference in ps
        self.detectors = []

    def init(self):
        pass

    def get(self, photon):
        detector_num = numpy.random.choice([0, 1])
        quantum_state = photon.quantum_state
        time = 0
        random = numpy.random.random_sample()

        if quantum_state == [complex(1), complex(0)]:  # Early
            if random <= 0.5:
                time = 0
            else:
                time = self.path_difference
        if quantum_state == [complex(0), complex(1)]:  # Late
            if random <= 0.5:
                time = self.path_difference
            else:
                time = 2 * self.path_difference
        if quantum_state == [complex(math.sqrt(2)), complex(math.sqrt(2))]:  # Early + Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 0:
                time = self.path_difference
            else:
                return
        if quantum_state == [complex(math.sqrt(2)), complex(-math.sqrt(2))]:  # Early - Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 1:
                time = self.path_difference
            else:
                return

        process = Process(self.detectors[detector_num], "get", [])
        event = Event(self.timeline.now() + time, process)
        self.timeline.schedule(event)

    def get_detection_times(self):
        times = []
        for d in self.detectors:
            times.append(d.photon_times)
        return times


class Switch(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)
        self.receivers = []
        self.start_time = 0
        self.frequency = 0
        self.state_list = [0]

    def init(self):
        pass

    def add_receiver(self, entity):
        self.receivers.append(entity)

    def set_state(self, state):
        self.state_list = [state]

    def get(self, photon):
        index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
        if index < 0 or index >= len(self.state_list):
            index = 0
        self.receivers[self.state_list[index]].get(photon)


class Node(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.components = kwargs.get("components", {})
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        self.message = None  # temporary storage for message received through classical channel
        self.protocol = None

    def init(self):
        pass

    def send_qubits(self, basis_list, bit_list, source_name):
        state_list = []
        for i, bit in enumerate(bit_list):
            state = (self.encoding_type["bases"][basis_list[i]])[bit]
            state_list.append(state)

        self.components[source_name].emit(state_list)

    def get_bits(self, light_time, start_time, frequency):
        bits = [-1] * int(round(light_time * frequency))  # -1 used for invalid bits

        if self.encoding_type["name"] == "polarization":
            detection_times = self.components["detector"].get_photon_times()

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    bits[index] = 0

            for time in detection_times[1]:  # detection times for |1> detector
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    if bits[index] == 0:
                        bits[index] = -1
                    else:
                        bits[index] = 1

            return bits

        elif self.encoding_type["name"] == "time_bin":
            detection_times_phase = self.components["interferometer"].get_photon_times()
            bin_separation = self.encoding_type["bin_separation"]

            for time in detection_times_phase[0]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and\
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    bits[index] = 0

            for time in detection_times_phase[1]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and\
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == 0:
                        bits[index] = -1
                    else:
                        bits[index] = 1

            return bits

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def set_bases(self, basis_list, start_time, frequency):
        basis_start_time = start_time - 1e12 / (2 * frequency)

        if self.encoding_type["name"] == "polarization":
            splitter = self.components["detector"].splitter
            splitter.start_time = basis_start_time
            splitter.frequency = frequency

            splitter_basis_list = []
            for b in basis_list:
                splitter_basis_list.append(self.encoding_type["bases"][b])
            splitter.basis_list = splitter_basis_list

        elif self.encoding_type["name"] == "time_bin":
            switch = self.components["detector"].switch
            switch.start_time = basis_start_time
            switch.frequency = frequency
            switch.state_list = basis_list

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def get_source_count(self):
        source = self.components['lightsource']
        return source.photon_counter

    def send_message(self, msg):
        self.components['cchannel'].transmit(msg, self)

    def receive_message(self, msg):
        self.message = msg
        # signal to protocol that we've received a message
        self.protocol.received_message()


class Topology:
    def __init__(self, config_file, timelines):
        self.nodes = {}
        self.quantum_channel = {}
        self.entities = []

        topo_config = json5.load(open(config_file))
        nodes_config = topo_config['nodes']
        self.create_nodes(nodes_config, timelines)
        self.create_qchannel(topo_config['QChannel'], timelines)
        self.create_cchannel(topo_config['CChannel'], timelines)
        self.create_protocols(nodes_config, timelines)

    def create_nodes(self, nodes_config, timelines):
        for node_config in nodes_config:
            components = {}

            for component_config in node_config['components']:
                if component_config['name'] in components:
                    raise Exception('two components have same name')

                # get component_name, timeline, and name
                # then delete entries in component_config dictionary to prevent conflicting values
                component_name = component_config['name']
                name = node_config['name'] + '.' + component_name
                tl = timelines[component_config['timeline']]
                del component_config['name']
                del component_config['timeline']

                # light source instantiation
                if component_config["type"] == 'LightSource':
                    ls = LightSource(name, tl, **component_config)
                    components[component_name] = ls
                    self.entities.append(ls)

                # detector instantiation
                elif component_config["type"] == 'QSDetector':
                    detector = QSDetector(name, tl, **component_config)
                    components[component_name] = detector
                    self.entities.append(detector)

                else:
                    raise Exception('unknown device type')

            node = Node(node_config['name'], timelines[node_config['timeline']], components=components)

            for protocol_config in node_config['protocols']:
                protocol_name = protocol_config['name']
                name = node_config['name'] + '.' + protocol_name
                tl = timelines[protocol_config['timeline']]
                del protocol_config['name']
                del protocol_config['timeline']

                if protocol_config["protocol"] == 'BB84':
                    bb84 = BB84(name, tl, **protocol_config)
                    bb84.assign_node(node)
                    node.protocol = bb84
                    self.entities.append(bb84)

                # add cascade config

            self.entities.append(node)

            if node.name in self.nodes:
                raise Exception('two nodes have same name')

            self.nodes[node.name] = node

    def create_qchannel(self, channel_config, timelines):
        for config in channel_config:
            name = config['name']
            tl = timelines[config['timeline']]
            sender = self.find_entity_by_name(config['sender'])
            receiver = self.find_entity_by_name(config['receiver'])
            del config['name']
            del config['timeline']
            del config['sender']
            del config['receiver']

            chan = QuantumChannel(name, tl, **config)
            chan.set_sender(sender)
            sender.direct_receiver = chan
            chan.set_receiver(receiver)
            self.entities.append(chan)

    # TODO: use add_end function for classical channel
    def create_cchannel(self, channel_config, timelines):
        for config in channel_config:
            name = config['name']
            tl = timelines[config['timeline']]
            del config['name']
            del config['timeline']

            chan = ClassicalChannel(name, tl, **config)
            self.entities.append(chan)

    # TODO: populate
    def create_protocols(self, nodes_config, timelines):
        pass

    def print_topology(self):
        pass

    def to_json5_file(self):
        pass

    def find_entity_by_name(self, name):
        for e in self.entities:
            if e.name == name:
                return e
        raise Exception('unknown entity name',name)

    def find_node_by_name(self, name):
        pass

    def find_qchannel_by_name(self, name):
        pass

