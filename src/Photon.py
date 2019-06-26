from entity import Entity


class Photon(Entity):

    def __init__(self, timeline, frequency, name=None):
        Entity.__init__(self, timeline, name)
        self.frequency = frequency

    def init(self):
        pass
