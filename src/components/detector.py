import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class Detector(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = kwargs.get("efficiency", 1)
        self.dark_count = kwargs.get("dark_count", 0)  # measured in Hz
        self.count_rate = kwargs.get("count_rate", math.inf)  # measured in Hz
        self.time_resolution = kwargs.get("time_resolution", 1)  # measured in ps
        self.next_detection_time = 0
        self.photon_counter = 0

    def init(self):
        self.add_dark_count()

    def get(self, dark_get=False):
        self.photon_counter += 1
        now = self.timeline.now()
        time = int(round(now / self.time_resolution) * self.time_resolution)

        if (numpy.random.random_sample() < self.efficiency or dark_get) and now > self.next_detection_time:
            self._pop(detector=self, time=time)
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def add_dark_count(self):
        if self.dark_count > 0:
            time_to_next = int(numpy.random.exponential(1 / self.dark_count) * 1e12)  # time to next dark count
            time = time_to_next + self.timeline.now()  # time of next dark count

            process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
            process2 = Process(self, "get", [True])
            event1 = Event(time, process1)
            event2 = Event(time, process2)
            self.timeline.schedule(event1)
            self.timeline.schedule(event2)


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

