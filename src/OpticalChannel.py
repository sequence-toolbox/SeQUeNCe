from entity import Entity
from event import Event
from process import Process
from Node import Node
import numpy


class OpticalChannel(Entity):

    def __init__(self, timeline, name=None, **kwargs):
        Entity.__init__(self, timeline, name)
        self.attenuation = kwargs.get("attenuation", 0)
        self.distance = kwargs.get("distance", 0)
        self.temperature = kwargs.get("temperature", 0)
        self.fidelity = kwargs.get("fidelity", 1)
        self.sender = None
        self.receiver = None
        self.light_speed = 3 * 10 ** -4  # used for photon timing calculations

    def init(self):
        pass

    def transmit(self, photon):
        # generate chance to lose photon
        loss = self.distance * self.attenuation
        chance_photon_kept = 10 ** (loss / -20)
        chance_photon_kept *= self.fidelity

        # check if photon kept
        if numpy.random.random < chance_photon_kept:
            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + int(self.distance/self.light_speed)
            process = Process(self.receiver, Node.receive_photon, [photon])

            event = Event(future_time, process)
            self.timeline.schedule(event)

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

    def change_distance(self):
        # update distance based on temperature
        self.distance = self.distance
