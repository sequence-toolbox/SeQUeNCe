import numpy

from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process


class OpticalChannel(Entity):
    def __init__(self, name, timeline, attenuation, distance, **kwargs):
        Entity.__init__(self, name, timeline)
        self.attenuation = attenuation
        self.distance = distance  # (measured in m)
        self.polarization_fidelity = kwargs.get("polarization_fidelity", 1)
        self.light_speed = kwargs.get("light_speed",
                                      2 * 10 ** -4)  # used for photon timing calculations (measured in m/ps)
        self.chromatic_dispersion = kwargs.get("cd", 17)  # measured in ps / (nm * km)

    def init(self):
        pass

    def set_distance(self, distance):
        self.distance = distance


class QuantumChannel(OpticalChannel):
    def __init__(self, name, timeline, attenuation, distance, **kwargs):
        super().__init__(name, timeline, attenuation, distance, **kwargs)
        self.sender = None
        self.receiver = None
        self.depo_counter = 0
        self.photon_counter = 0
        self.delay = 0
        self.loss = 1

    def init(self):
        self.delay = round(self.distance / self.light_speed)
        self.loss = 1 - 10 ** (self.distance * self.attenuation / -10)

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

    def get(self, photon):
        assert self.delay != 0 and self.loss != 1, "QuantumChannel forgets to run init() function"
        # check if photon kept
        if photon.is_null or numpy.random.random_sample() > self.loss:
            self.photon_counter += 1

            # check if random polarization noise applied
            if numpy.random.random_sample() > self.polarization_fidelity and \
                    photon.encoding_type["name"] == "polarization":
                photon.random_noise()
                self.depo_counter += 1

            # schedule receiving node to receive photon at future time determined by light speed and dispersion
            future_time = self.timeline.now() + self.delay
            # dispersion_time = int(round(self.chromatic_dispersion * photon.wavelength * self.distance * 1e-3))

            process = Process(self.receiver, "get", [photon])
            event = Event(future_time, process)
            self.timeline.schedule(event)
        else:
            pass


class ClassicalChannel(OpticalChannel):
    def __init__(self, name, timeline, attenuation, distance, **kwargs):
        super().__init__(name, timeline, attenuation, distance, **kwargs)
        self.ends = []
        self.delay = kwargs.get("delay", (self.distance / self.light_speed))

    def add_end(self, node):
        if (node in self.ends):
            raise Exception("already have endpoint", node)
        if len(self.ends) == 2:
            raise Exception("channel already has 2 endpoints")

        self.ends.append(node)

    def set_ends(self, end1, end2):
        self.ends.append(end1)
        self.ends.append(end2)
        end1.assign_cchannel(self, end2.name)
        end2.assign_cchannel(self, end1.name)

    def transmit(self, message, source, priority: int):
        # get node that's not equal to source
        if source not in self.ends:
            raise Exception("no endpoint", source)

        receiver = None
        for e in self.ends:
            if e != source:
                receiver = e

        future_time = int(round(self.timeline.now() + int(self.delay)))
        process = Process(receiver, "receive_message", [source.name, message])
        event = Event(future_time, process, priority)
        self.timeline.schedule(event)