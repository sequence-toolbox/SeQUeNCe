import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


# class for photon memory
class Memory_EIT(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.photon = None

    def init(self):
        pass

    def get(self, photon):
        photon.location = self
        self.photon = photon

    def retrieve_photon(self):
        photon = self.photon
        self.photon = None
        return photon
