from entity import Entity
from Photon import Photon


class LightSource(Entity):

    def __init__(self, timeline, frequency, wavelength, mean_photon_num, encoding_type, direct_receiver, name=None):
        Entity.__init__(self, timeline, name)
        self.frequency = frequency
        self.wavelength = wavelength
        self.mean_photon_num = mean_photon_num
        self.encoding_type = encoding_type
        self.direct_receiver = direct_receiver
        self.photon_counter = 0

    def init(self):
        pass

    # emit_photon does not currently account for poisson distribution
    def emit_photon(self):
        photon = Photon(self.timeline, self.wavelength, "photon")
        # TODO: figure out photon naming scheme

        self.timeline.entities.append(photon)
        self.direct_receiver.transmit_photon(photon)

        self.photon_counter += 1


class Detector(Entity):

    def __init__(self, timeline, efficiency, dark_count, count_rate, time_resolution, name=None):
        Entity.__init__(self, timeline, name)
        self.efficiency = efficiency
        self.dark_count = dark_count
        self.count_rate = count_rate
        self.time_resolution = time_resolution

    def init(self):
        pass

    def measure_photon(self, photon):
        self.timeline.entities.remove(photon)
        return photon.frequency


class Memory(Entity):

    def __init__(self, timeline, decoherence, efficiency, fidelity, name=None):
        Entity.__init__(self, timeline, name)
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

        self.source.direct_receiver = connected_channel

    def init(self):
        pass

    def send_photon(self):
        # use emitter to send photon over connected channel to node
        self.source.emit_photon()

    def receive_photon(self, photon):
        # use detector to sense photon (return frequency information)
        return self.detector.measure_photon(photon)
