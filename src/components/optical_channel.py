import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


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

    # def set_temerature_model(self, filename):
    #     self.tModel = TemperatureModel()
    #     self.tModel.read_temperature_file(filename)


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
        if photon.is_null or numpy.random.random_sample() < chance_photon_kept:
            self.photon_counter += 1

            # check if random polarization noise applied
            if numpy.random.random_sample() > self.polarization_fidelity and\
                    photon.encoding_type["name"] == "polarization":
                photon.random_noise()
                self.depo_counter+=1

            # schedule receiving node to receive photon at future time determined by light speed and dispersion
            future_time = self.timeline.now() + round(self.distance / self.light_speed)
            # dispersion_time = int(round(self.chromatic_dispersion * photon.wavelength * self.distance * 1e-3))

            process = Process(self.receiver, "get", [photon])
            event = Event(future_time, process)
            self.timeline.schedule(event)
        else:
            photon.remove_from_timeline()


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

    def set_ends(self, node_list):
        for node in node_list:
            self.add_end(node)
        for node in node_list:
            node.assign_cchannel(self)

    def transmit(self, message, source, priority):
        # get node that's not equal to source
        if source not in self.ends:
            Exception("no endpoint", source)

        receiver = None
        for e in self.ends:
            if e != source:
                receiver = e

        future_time = int(round(self.timeline.now() + int(self.delay)))
        process = Process(receiver, "receive_message", [source.name, message])
        event = Event(future_time, process, priority)
        self.timeline.schedule(event)

        
