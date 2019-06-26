from entity import Entity
from Photon import Photon


class LightSource(Entity):

    def __init__(self, timeline, node, rate, frequency, jitter, name=None):
        Entity.__init__(self, timeline, name)
        self.node = node
        self.rate = rate
        self.frequency = frequency
        self.jitter = jitter

    def init(self):
        pass

    # emit_photon does not currently account for poisson distribution
    def emit_photon(self, channel, node):
        photon = Photon(self.timeline, self.frequency, self.node.name + "photon")
        # TODO: figure out photon naming scheme

        self.timeline.entities.append(photon)
        channel.transmit_photon(photon, node)


class Detector(Entity):

    def __init__(self, timeline, node, rate, efficiency, dark_count, jitter, name=None):
        Entity.__init__(self, timeline, name)
        self.node = node
        self.rate = rate
        self.efficiency = efficiency
        self.dark_count = dark_count
        self.jitter = jitter

    def init(self):
        pass

    def measure_photon(self, photon):
        self.timeline.entities.remove(photon)
        return photon.frequency


class Memory(Entity):

    def __init__(self, timeline, node, decoherence, efficiency, fidelity, name=None):
        Entity.__init__(self, timeline, name)
        self.node = node
        self.decoherence = decoherence
        self.efficiency = efficiency
        self.fidelity = fidelity

    def init(self):
        pass


class Node(Entity):

    def __init__(self, timeline, memory=None, source=None, detector=None, connected_channel=None, name=None):
        Entity.__init__(self, timeline, name)
        self.memory = memory
        self.source = source
        self.detector = detector
        self.connected_channel = connected_channel

    def init(self):
        pass

    def send_photon(self, node):
        # use emitter to send photon over connected channel to node
        self.source.emit_photon(self.connected_channel, node)

    def receive_photon(self, photon):
        # use detector to sense photon (return frequency information)
        return self.detector.measure_photon(photon)
