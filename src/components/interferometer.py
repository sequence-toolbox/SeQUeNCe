import math
import copy
import numpy

from ..kernel.process import Process
from ..kernel.entity import Entity
from ..kernel.event import Event


class Interferometer(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)
        self.path_difference = kwargs.get("path_difference", 0)  # time difference in ps
        self.phase_error = kwargs.get("phase_error", 0)  # chance of measurement error in phase
        self.detectors = []

    def init(self):
        pass

    def get(self, photon):
        detector_num = numpy.random.choice([0, 1])
        quantum_state = photon.quantum_state
        time = 0
        random = numpy.random.random_sample()

        if quantum_state == [complex(1), complex(0)]:  # Early
            if random <= 0.5:
                time = 0
            else:
                time = self.path_difference
        if quantum_state == [complex(0), complex(1)]:  # Late
            if random <= 0.5:
                time = self.path_difference
            else:
                time = 2 * self.path_difference

        if numpy.random.random_sample() < self.phase_error:
            quantum_state = list(numpy.multiply([1, -1], quantum_state))

        if quantum_state == [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]:  # Early + Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 0:
                time = self.path_difference
            else:
                return
        if quantum_state == [complex(math.sqrt(1/2)), complex(-math.sqrt(1/2))]:  # Early - Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 1:
                time = self.path_difference
            else:
                return

        process = Process(self.detectors[detector_num], "get", [])
        event = Event(self.timeline.now() + time, process)
        self.timeline.schedule(event)

