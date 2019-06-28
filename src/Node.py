from entity import Entity
from event import Event
from Photon import Photon
from process import Process
import math
import numpy


class LightSource(Entity):

    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.frequency = kwargs.get("frequency", 0)  # measured in Hz
        self.wavelength = kwargs.get("wavelength", 0)  # measured in nm
        self.mean_photon_num = kwargs.get("mean_photon_num", 0)
        self.encoding_type = kwargs.get("encoding_type")
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.quantum_state = kwargs.get("quantum_state", [complex(1), complex(0)])
        self.photon_counter = 0

    def init(self):
        pass

    def emit(self, time):
        freq_pico = self.frequency / (10 ** 12)  # frequency in THz
        num_pulses = int(time * freq_pico)
        photons = numpy.random.poisson(self.mean_photon_num, num_pulses)
        current_time = self.timeline.now()

        for i in range(num_pulses):
            if photons[i] > 0:
                new_photon = Photon(self.timeline, self.wavelength, self.direct_receiver, self.encoding_type, self. quantum_state)
                process = Process(self.direct_receiver, self.direct_receiver.transmit, [new_photon])

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
        self.photon_counter = 0
        self.photons_past_second = 0

    def init(self):
        pass

    def detect(self, photon):
        if numpy.random.random < self.efficiency & self.photons_past_second < self.count_rate:
            self.photon_counter += 1

            self.photons_past_second += 1
            process = Process(self, self.decrease_pps_count)
            event = Event(self.timeline.now() + (10 ** 12), process)
            self.timeline.schedule(event)

    def add_dark_count(self):
        self.photon_counter += self.timeline.now() * (self.dark_count / (10 ** 12))

    def decrease_pps_count(self):
        self.photons_past_second -= 1


class Node(Entity):

    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.components = kwargs.get("components", {})

    def init(self):
        pass

    def send_photon(self, time):
        # use emitter to send photon over connected channel to node
        self.components["LightSource"].emit(time)

    def receive_photon(self, photon):
        self.components["Detector"].detect(photon)

    def get_photon_count(self):
        self.components["Detector"].add_dark_count()
        return self.components["Detector"].photon_counter
