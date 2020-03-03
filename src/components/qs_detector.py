import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class QSDetector(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)

        detectors = kwargs.get("detectors", [])
        if (self.encoding_type["name"] == "polarization" and len(detectors) != 2) or\
                (self.encoding_type["name"] == "time_bin" and len(detectors) != 3):
            raise Exception("invalid number of detectors specified")
        self.detectors = []
        for d in detectors:
            if d is not None:
                detector = Detector(timeline, **d)
            else:
                detector = None
            self.detectors.append(detector)

        # protocol unique initialization

        if self.encoding_type["name"] == "polarization":
            # set up beamsplitter
            splitter = kwargs.get("splitter")
            self.splitter = BeamSplitter(timeline, **splitter)
            self.splitter.receivers = self.detectors

        elif self.encoding_type["name"] == "time_bin":
            # set up switch and interferometer
            interferometer = kwargs.get("interferometer")
            self.interferometer = Interferometer(timeline, **interferometer)
            self.interferometer.detectors = self.detectors[1:]
            switch = kwargs.get("switch")
            self.switch = Switch(timeline, **switch)
            self.switch.receivers = [self.detectors[0], self.interferometer]

        else:
            raise Exception("invalid encoding type for QSDetector " + self.name)

    def init(self):
        pass

    def get(self, photon):
        if self.encoding_type["name"] == "polarization":
            self.splitter.get(photon)

        elif self.encoding_type["name"] == "time_bin":
            self.switch.get(photon)

    def pop(self, **kwargs):
        detector = kwargs.get("detector")
        self._pop(entity="QSDetector", detector_num=self.detectors.index(detector))

    def set_basis(self, basis):
        self.splitter.set_basis(basis)

