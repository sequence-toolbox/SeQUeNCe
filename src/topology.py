import math
import numpy
import json5
import pandas as pd

from process import Process
from entity import Entity
from event import Event


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
        self.encoding_type = kwargs.get("encoding_type")
        qs_array = kwargs.get("quantum_state", [[math.sqrt(1 / 2), 0], [math.sqrt(1 / 2), 0]])
        self.quantum_state = [complex(*qs_array[0]), complex(*qs_array[1])]  # convert to complex number

    def init(self):
        pass

    def random_noise(self):
        pass

    def measure(self, basis):
        alpha = numpy.dot(self.quantum_state, basis[0])  # projection onto basis vector
        if numpy.random.random_sample() < (alpha ** 2).real:
            return 0
        return 1


class OpticalChannel(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.attenuation = kwargs.get("attenuation", 0)
        self.distance = kwargs.get("distance", 0)
        self.temperature = kwargs.get("temperature", 0)
        self.sender = None
        self.receiver = None
        self.light_speed = kwargs.get("light_speed",
                                      3 * 10 ** -4)  # used for photon timing calculations (measured in m/ps)

    def init(self):
        pass

    def transmit(self, photon):
        # generate chance to lose photon
        loss = self.distance * self.attenuation
        chance_photon_kept = 10 ** (loss / -10)

        # check if photon kept
        if numpy.random.random_sample() < chance_photon_kept:
            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + int(self.distance / self.light_speed)
            process = Process(self.receiver, "detect", [photon])

            event = Event(future_time, process)
            self.timeline.schedule(event)

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

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


class LightSource(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.frequency = kwargs.get("frequency", 0)  # measured in Hz
        self.wavelength = kwargs.get("wavelength", 0)  # measured in nm
        self.mean_photon_num = kwargs.get("mean_photon_num", 0)
        self.encoding_type = kwargs.get("encoding_type")
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.quantum_state = kwargs.get("quantum_state", [complex(math.sqrt(2)), complex(math.sqrt(2))])
        self.photon_counter = 0

    def init(self):
        pass

    def emit(self, time):
        freq_pico = self.frequency / (10 ** 12)  # frequency in THz
        num_pulses = int(time * freq_pico)
        photons = numpy.random.poisson(self.mean_photon_num, num_pulses)
        current_time = self.timeline.now()

        for i in range(num_pulses):
            for _ in range(photons[i]):
                new_photon = Photon(None, self.timeline,
                                    wavelength=self.wavelength,
                                    location=self.direct_receiver,
                                    encoding_type=self.encoding_type,
                                    quantum_state=self.quantum_state)
                process = Process(self.direct_receiver, "transmit", [new_photon])

                time = current_time + (i / freq_pico)
                event = Event(time, process)

                self.timeline.schedule(event)

                self.photon_counter += 1

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver


class Detector(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.efficiency = kwargs.get("efficiency", 1)
        self.dark_count = kwargs.get("dark_count", 0)  # measured in Hz
        self.count_rate = kwargs.get("count_rate", math.inf)  # measured in Hz
        self.time_resolution = kwargs.get("time_resolution", 0)  # measured in ps(?)
        self.basis = kwargs.get("basis", [[1, 0], [0, 1]])
        self.photon_counter = [0, 0]
        self.photons_past_second = 0
        self.detected_in_resolution = False

    def init(self):
        pass

    def detect(self, photon):
        if numpy.random.random_sample() < self.efficiency and self.photons_past_second < self.count_rate \
                and not self.detected_in_resolution:

            self.photon_counter[photon.measure(self.basis)] += 1

            self.photons_past_second += 1
            self.detected_in_resolution = True

            # schedule event to decrease the count of photons in the past second by 1 in 1 second
            process = Process(self, "decrease_pps_count", [])
            event = Event(self.timeline.now() + (10 ** 12), process)
            self.timeline.schedule(event)

            # schedule event to reset detected_in_resolution after 1 resolution time
            process = Process(self, "reset_timestep", [])
            event = Event(self.timeline.now() + self.time_resolution, process)
            self.timeline.schedule(event)

    def add_dark_count(self):
        return self.timeline.now() * (self.dark_count / (10 ** 12))

    def decrease_pps_count(self):
        self.photons_past_second -= 1

    def reset_timestep(self):
        self.detected_in_resolution = False


class Node(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.components = kwargs.get("components", {})

    def init(self):
        pass

    def send_photon(self, time, source_name):
        # use emitter to send photon over connected channel to node
        self.components[source_name].emit(time)

    def receive_photon(self, photon, detector_name):
        self.components[detector_name].detect(photon)

    def get_photon_count(self, detector_name):
        dark_count = self.components[detector_name].add_dark_count()
        return self.components[detector_name].photon_counter + dark_count


class Topology:
    def __init__(self, config_file, timelines):
        self.nodes = {}
        self.quantum_channel = {}
        self.entities = []

        topo_config = json5.load(open(config_file))
        nodes_config = topo_config['nodes']
        self.create_nodes(nodes_config, timelines)
        qchannel_config = topo_config['QChannel']
        self.create_qchannel(qchannel_config, timelines)

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
                elif component_config["type"] == 'Detector':
                    detector = Detector(name, tl, **component_config)
                    components[component_name] = detector
                    self.entities.append(detector)

                else:
                    raise Exception('unknown device type')

            node = Node(node_config['name'], timelines[node_config['timeline']], **components)
            self.entities.append(node)

            if node.name in self.nodes:
                raise Exception('two nodes have same name')

            self.nodes[node.name] = node

    def create_qchannel(self, qchannel_config, timelines):
        for qc_config in qchannel_config:
            name = qc_config['name']
            tl = timelines[qc_config['timeline']]
            del qc_config['name']
            del qc_config['timeline']

            qc = OpticalChannel(name, tl, **qc_config)

            sender = self.find_entity_by_name(qc_config['sender'])
            receiver = self.find_entity_by_name(qc_config['receiver'])

            qc.set_sender(sender)
            sender.direct_receiver = qc
            qc.set_receiver(receiver)
            self.entities.append(qc)

    def print_topology(self):
        pass

    def to_json5_file(self):
        pass

    def find_entity_by_name(self, name):
        for e in self.entities:
            if e.name == name:
                return e
        raise Exception('unknown entity name')

    def find_node_by_name(self, name):
        pass

    def find_qchannel_by_name(self, name):
        pass

