from entity import Entity
from Photon import Photon


class LightSource(Entity):

    def __init__(self, timeline, frequency, wavelength, mean_photon_num, encoding_type, state, name=None):
        Entity.__init__(self, timeline, name)
        self.frequency = frequency
        self.wavelength = wavelength
        self.mean_photon_num = mean_photon_num
        self.encoding_type = encoding_type
        self.direct_receiver = None
        self.photon_counter = 0
        self.quantum_state = state

    def init(self):
        pass

    # emit_photon does not currently account for poisson distribution
    def emit_photon(self, time):
        photon = Photon(self.timeline, self.wavelength,
                        self.direct_receiver, self.encoding_type, self.quantum_state, "photon")
        # TODO: figure out photon naming scheme

        self.timeline.entities.append(photon)
        self.direct_receiver.transmit(photon)

        self.photon_counter += 1

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver


class Detector(Entity):

    def __init__(self, timeline, efficiency, dark_count, count_rate, time_resolution, name=None):
        Entity.__init__(self, timeline, name)
        self.efficiency = efficiency
        self.dark_count = dark_count
        self.count_rate = count_rate
        self.time_resolution = time_resolution

    def init(self):
        pass

    def detect(self, photon):
        pass


class Memory(Entity):

    def __init__(self, timeline, decoherence, efficiency, fidelity, name=None):
        Entity.__init__(self, timeline, name)
        self.decoherence = decoherence
        self.efficiency = efficiency
        self.fidelity = fidelity

    def init(self):
        pass


class Node(Entity):

    def __init__(self, timeline, components=None, name=None):
        Entity.__init__(self, timeline, name)
        self.components = components

    def init(self):
        pass

    def send_photon(self, time):
        # use emitter to send photon over connected channel to node
        self.components["light_source"].emit(time)

    def receive_photon(self, photon):
        self.components["detector"].detect(photon)
