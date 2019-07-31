import math
from typing import List, Any

import numpy
import json5

import encoding
from process import Process
from entity import Entity
from event import Event

from BB84 import BB84


"""
import pandas as pd
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
"""


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
        self.distance = kwargs.get("distance", 0)  # (measured in m)
        self.temperature = kwargs.get("temperature", 0)
        self.polarization_fidelity = kwargs.get("polarization_fidelity", 1)
        self.light_speed = kwargs.get("light_speed",
                                      3 * 10 ** -4)  # used for photon timing calculations (measured in m/ps)
        self.chromatic_dispersion = kwargs.get("cd", 17)  # measured in ps / (nm * km)

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
            self.photon_counter += 1

            # check if random polarization noise applied
            if numpy.random.random_sample() > self.polarization_fidelity and\
                    photon.encoding_type["name"] == "polarization":
                photon.random_noise()
                self.depo_counter+=1

            # schedule receiving node to receive photon at future time determined by light speed and dispersion
            future_time = self.timeline.now() + int(self.distance / self.light_speed)
            # dispersion_time = int(round(self.chromatic_dispersion * photon.wavelength * self.distance * 1e-3))

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
        self.wavelength = kwargs.get("wavelength", 1550)  # measured in nm
        self.linewidth = kwargs.get("bandwidth", 0)  # st. dev. in photon wavelength (nm)
        self.mean_photon_num = kwargs.get("mean_photon_num", 0)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.photon_counter = 0
        # for BB84
        # self.basis_lists = []
        # self.basis_list = []
        # self.bit_lists = []
        # self.bit_list = []
        # self.is_on = False
        # self.pulse_id = 0

    def init(self):
        pass

    # for general use
    def emit(self, state_list):
        time = self.timeline.now()

        for i, state in enumerate(state_list):
            num_photons = numpy.random.poisson(self.mean_photon_num)

            for _ in range(num_photons):
                wavelength = self.linewidth * numpy.random.randn() + self.wavelength
                new_photon = Photon(None, self.timeline,
                                    wavelength=wavelength,
                                    location=self.direct_receiver,
                                    encoding_type=self.encoding_type,
                                    quantum_state=state)
                process = Process(self.direct_receiver, "get", [new_photon])
                event = Event(int(round(time)), process)
                self.timeline.schedule(event)

                self.photon_counter += 1

            time += 1e12 / self.frequency

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
            self.interferometer.detectors = self.detectors[1:]
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
        self.path_difference = kwargs.get("path_difference", 0)  # time difference in ps
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
        if quantum_state == [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]:  # Early + Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 0:
                time = self.path_difference
            else:
                return
        if quantum_state == [complex(math.sqrt(1/2)), complex(-math.sqrt(1/2))]:  # Early - Late
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

        receiver = self.receivers[self.state_list[index]]
        # check if receiver is detector, if we're using time bin, and if the photon is "late" to schedule measurement
        if isinstance(receiver, Detector):
            if photon.encoding_type["name"] == "time_bin" and photon.measure(photon.encoding_type["bases"][0]):
                time = self.timeline.now() + photon.encoding_type["bin_separation"]
                process = Process(receiver, "get", [])
                event = Event(time, process)
                self.timeline.schedule(event)
            else:
                receiver.get()
        else:
            receiver.get(photon)


class BSM(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.encoding_type = kwargs.get("encoding_type", encoding.time_bin)

        # two detectors for time-bin encoding
        # four detectors for polarization encoding
        self.detectors = kwargs.get("detectors",[])
        if self.encoding_type["name"] == "polarization":
            assert len(self.detectors) == 4
        elif self.encoding_type["name"] == "time_bin":
            assert len(self.detectors) == 2

        # assume BSM is connected to two quantum channel
        # self.target_end = None
        # self.signal_end = None

        self.target_photon = None
        self.target_arrive_time = None
        self.signal_photon = None
        self.signal_arrive_time = None

    '''
    def assign_target_end(self, target_end):
        self.target_end = target_end

    def assign_signal_end(self, signal_end):
        self.signal_end = signal_end
    '''

    def init(self):
        pass

    def get(self, photon, photon_type):
        # record arrive time
        # if target photon and signal photon arrive at the same time, do measurement
        if photon_type == 0:
            # target photon
            self.target_photon = photon
            self.target_arrive_time = self.timeline.now()
        else:
            # signal photon
            self.signal_photon = photon
            self.signal_arrive_time = self.timeline.now()

        if not self.target_photon is None and not self.signal_photon is None:
            if self.target_arrive_time == self.signal_arrive_time:
                self.send_to_detectors()

    def send_to_detectors(self):
        # TODO: generalize function to any quantum entanglement state
        def get_another_photon(photon):
            for _photon in photon.entangled_photons:
                if _photon != photon: return _photon
            return

        if self.encoding_type["name"] == "time_bin":
            early_time = self.timeline.now()
            late_time = early_time + self.encoding_type["bin_separation"]
            random_num = numpy.random.random_sample()
            if random_num < 0.125:
                # project to |\phi_0> = |01> - |10>
                # |\phi_1> ---> - \beta |0> + \alpha |1>
                # |e> at d0, |l> at d1
                # TODO: change photons quantum state
                another_photon = get_another_photon(self.signal_photon)
                another_photon.entangled_photons = [another_photon]
                another_photon.quantum_state = [-target_photon.quantum_state[1], target_photon.quantum_state[0]]

                process = Process(self.detectors[0], "get", [self.target_photon])
                event = Event(int(round(early_time)), process)
                self.timeline.schedule(event)
                process = Process(self.detectors[1], "get", [self.signal_photon])
                event = Event(int(round(late_time)), process)
                self.timeline.schedule(event)

            elif random_num < 0.25:
                # project to |\phi_0> = |01> - |10>
                # |\phi_1> ---> - \beta |0> + \alpha |1>
                # |l> at d0, |e> at d1
                another_photon = get_another_photon(self.signal_photon)
                another_photon.entangled_photons = [another_photon]
                another_photon.quantum_state = [-target_photon.quantum_state[1], target_photon.quantum_state[0]]

                process = Process(self.detectors[0], "get", [self.target_photon])
                event = Event(int(round(late_time)), process)
                self.timeline.schedule(event)
                process = Process(self.detectors[1], "get", [self.signal_photon])
                event = Event(int(round(early_time)), process)
                self.timeline.schedule(event)

            elif random_num < 0.375:
                # project to |\phi_1> = |01> + |10>
                # |\phi_1> ---> \beta |0> + \alpha |1>
                # |e>, |l> at d0
                another_photon = get_another_photon(self.signal_photon)
                another_photon.entangled_photons = [another_photon]
                another_photon.quantum_state = [target_photon.quantum_state[1], target_photon.quantum_state[0]]

                process = Process(self.detectors[0], "get", [self.target_photon])
                event = Event(int(round(late_time)), process)
                self.timeline.schedule(event)
                process = Process(self.detectors[0], "get", [self.signal_photon])
                event = Event(int(round(early_time)), process)
                self.timeline.schedule(event)

            elif random_num < 0.5:
                # project to |\phi_1> = |01> + |10>
                # |\phi_1> ---> \beta |0> + \alpha |1>
                # |e>, |l> at d1
                another_photon = get_another_photon(self.signal_photon)
                another_photon.entangled_photons = [another_photon]
                another_photon.quantum_state = [target_photon.quantum_state[1], target_photon.quantum_state[0]]

                process = Process(self.detectors[1], "get", [self.target_photon])
                event = Event(int(round(late_time)), process)
                self.timeline.schedule(event)
                process = Process(self.detectors[1], "get", [self.signal_photon])
                event = Event(int(round(early_time)), process)
                self.timeline.schedule(event)

            else:
                # discard photons
                pass
        else:
            #TODO: polarization
            pass

        pass

    def get_bsm_res(self):
        # bsm_res = [ [timestamp of early photon, res] ]
        # res: 0 -> \phi_0; 1 -> \phi_1
        bsm_res = []
        if self.encoding_type["name"] == "time_bin":
            d0_times = self.detectors[0].photon_times
            d1_times = self.detectors[1].photon_times
            bin_separation = self.encoding_type["bin_separation"]
            while d0_times and d1_times:
                if abs(d0_times[0] - d1_times[0]) == bin_separation:
                    res = [min(d0_times[0], d1_times[0]), 0]
                    bsm_res.append(res)
                    d0_times.pop(0)
                    d1_times.pop(0)
                elif len(d0_times)>1 and abs(d0_times[0] - d0_times[1]) == bin_separation:
                    res = [d0_times[0], 1]
                    bsm_res.append(res)
                    d0_times.pop(0)
                    d0_times.pop(0)
                elif len(d1_times)>1 and abs(d1_times[0] - d1_times[1]) == bin_separation:
                    res = [d1_times[0], 1]
                    bsm_res.append(res)
                    d1_times.pop(0)
                    d1_times.pop(0)
                else:
                    if d0_times[0] < d1_times[0]:
                        d0_times.pop(0)
                    else:
                        d1_times.pop(0)

            while len(d0_times) > 1:
                if d0_times[1] - d0_times[0] == bin_separation:
                    res = [d0_times[0], 1]
                    bsm_res.append(res)
                    d0_times.pop(0)
                d0_times.pop(0)

            while len(d1_times) > 1:
                if d1_times[1] - d1_times[0] == bin_separation:
                    res = [d1_times[0], 1]
                    bsm_res.append(res)
                    d1_times.pop(0)
                d1_times.pop(0)

        else:
            # TODO: polariation
            pass
        return bsm_res


class Node(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.components = kwargs.get("components", {})
        self.message = None  # temporary storage for message received through classical channel
        self.protocol = None

    def init(self):
        pass

    def send_qubits(self, basis_list, bit_list, source_name):
        encoding_type = self.components[source_name].encoding_type
        state_list = []
        for i, bit in enumerate(bit_list):
            state = (encoding_type["bases"][basis_list[i]])[bit]
            state_list.append(state)

        self.components[source_name].emit(state_list)

    def get_bits(self, light_time, start_time, frequency, detector_name):
        encoding_type = self.components[detector_name].encoding_type
        bits = [-1] * int(round(light_time * frequency))  # -1 used for invalid bits

        if encoding_type["name"] == "polarization":
            detection_times = self.components[detector_name].get_photon_times()

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

        elif encoding_type["name"] == "time_bin":
            detection_times = self.components[detector_name].get_photon_times()
            bin_separation = encoding_type["bin_separation"]

            # single detector (for early, late basis) times
            for time in detection_times[0]:
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    if abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                        bits[index] = 0
                    else:
                        bits[index] = 1

            # interferometer detector 0 times
            for time in detection_times[1]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and\
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == -1:
                        bits[index] = 0
                    else:
                        bits[index] = -1

            # interferometer detector 1 times
            for time in detection_times[2]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and\
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == -1:
                        bits[index] = 1
                    else:
                        bits[index] = -1

            return bits

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def set_bases(self, basis_list, start_time, frequency, detector_name):
        encoding_type = self.components[detector_name].encoding_type
        basis_start_time = start_time - 1e12 / (2 * frequency)

        if encoding_type["name"] == "polarization":
            splitter = self.components[detector_name].splitter
            splitter.start_time = basis_start_time
            splitter.frequency = frequency

            splitter_basis_list = []
            for b in basis_list:
                splitter_basis_list.append(encoding_type["bases"][b])
            splitter.basis_list = splitter_basis_list

        elif encoding_type["name"] == "time_bin":
            switch = self.components[detector_name].switch
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

