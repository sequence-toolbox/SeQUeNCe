from entity import Entity
import math


class Photon(Entity):

    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.wavelength = kwargs.get("wavelength", 0)
        self.location = kwargs.get("location", None)
        self.encoding_type = kwargs.get("encoding_type")
        self.quantum_state = kwargs.get("quantum_state", [complex(math.sqrt(2)), complex(math.sqrt(2))])

    def init(self):
        pass

    def random_noise(self):
        pass
