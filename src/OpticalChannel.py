from entity import Entity
from event import Event
from process import Process
import numpy


class OpticalChannel(Entity):

    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.attenuation = kwargs.get("attenuation", 0)
        self.distance = kwargs.get("distance", 0)
        self.temperature = kwargs.get("temperature", 0)
        self.sender = None
        self.receiver = None
        self.light_speed = 3 * 10 ** -4  # used for photon timing calculations (measured in m/ps)

    def init(self):
        pass

    def transmit(self, photon):
        # generate chance to lose photon
        loss = self.distance * self.attenuation
        chance_photon_kept = 10 ** (loss / -20)

        # check if photon kept
        if numpy.random.random_sample() < chance_photon_kept:
            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + int(self.distance/self.light_speed)
            process = Process(self.receiver, "detect", [photon])

            event = Event(future_time, process)
            self.timeline.schedule(event)

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

    def change_distance(self):
        # update distance based on temperature
        self.distance = self.distance
