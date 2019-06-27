from entity import Entity
from event import Event
from process import Process
from Node import Node
import numpy as np


class OpticalChannel(Entity):

    def __init__(self, timeline, attenuation, distance, temperature, fidelity, name=None):
        Entity.__init__(self, timeline, name)
        self.attenuation = attenuation
        self.distance = distance
        self.temperature = temperature
        self.fidelity = fidelity
        self.sender = None
        self.receiver = None
        self.light_speed = 3 * 10 ** -4 # used for photon timing calculations

    def init(self):
        pass

    def transmit(self, photon):
        # TODO: check if node connected to optical channel

        # generate chance to lose photon
        length = self.distance # calculate based on temp

        loss = length * self.attenuation
        chance_photon_kept = 10 ** (loss / -20)
        chance_photon_kept *= self.fidelity

        # check if photon lost
        if np.random.random > chance_photon_kept:
            self.timeline.entities.remove(photon)
        else:
            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + int(length/self.light_speed)
            process = Process(self.receiver, Node.receive_photon, [photon])

            event = Event(future_time, process)
            self.timeline.schedule(event)

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

    def change_distance(self, distance):
        self.distance = distance
