import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class BeamSplitter(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)  # Splitter is part of the QSDetector, and does not have its own name
        basis = kwargs.get("basis", [[complex(1), complex(0)], [complex(0), complex(1)]])
        self.fidelity = kwargs.get("fidelity", 1)
        self.receivers = []
        # for BB84
        self.start_time = 0
        self.frequency = 0
        self.basis_list = [basis]  # default value

    def init(self):
        pass

    def get(self, photon):
        if numpy.random.random_sample() < self.fidelity:
            index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
            if 0 <= index < len(self.basis_list):
                index = 0
            res = Photon.measure(self.basis_list[index], photon)
            self.receivers[res].get()

    def set_basis(self, basis):
        self.basis_list = [basis]
