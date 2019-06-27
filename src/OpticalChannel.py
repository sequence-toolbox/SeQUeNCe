from entity import Entity
from event import Event
from process import Process
from Node import Node


class OpticalChannel(Entity):

    def __init__(self, timeline, length, attenuation, temperature, fidelity, sender, receiver, name=None):
        Entity.__init__(self, timeline, name)
        self.length = length
        self.attenuation = attenuation
        self.temperature = temperature
        self.fidelity = fidelity
        self.sender = sender
        self.receiver = receiver

    def init(self):
        pass

    def transmit_photon(self, photon):
        # TODO: check if node connected to optical channel

        # future_time will be set based on speed of photon in future
        future_time = self.timeline.now() + 1
        process = Process(self.receiver, Node.receive_photon, [photon])

        event = Event(future_time, process)
        self.timeline.schedule(event)
