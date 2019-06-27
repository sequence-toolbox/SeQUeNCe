from entity import Entity


class Photon(Entity):

    def __init__(self, timeline, wavelength, location, encoding_type, quantum_state, name=None):
        Entity.__init__(self, timeline, name)
        self.wavelength = wavelength
        self.location = location
        self.encoding_type = encoding_type
        self.quantum_state = quantum_state

    def init(self):
        pass

    def random_noise(self):
        pass
