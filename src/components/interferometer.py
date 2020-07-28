from math import sqrt
from numpy import random
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..components.photon import Photon
    from ..components.detectors import Detector

from ..kernel.process import Process
from ..kernel.entity import Entity
from ..kernel.event import Event


class Interferometer(Entity):
    def __init__(self, name: str, timeline: "Timeline", path_diff, **kwargs):
        Entity.__init__(self, "", timeline)
        self.path_difference = path_diff  # time difference in ps
        self.phase_error = kwargs.get("phase_error", 0)  # chance of measurement error in phase
        self.receivers = []

    def init(self) -> None:
        assert len(self.receivers) == 2

    def set_receiver(self, index: int, receiver: "Detector") -> None:
        if index > len(self.receivers):
            raise Exception("index is larger than the length of receivers")
        self.receivers.insert(index, receiver)

    def get(self, photon: "Photon") -> None:
        detector_num = random.choice([0, 1])
        quantum_state = photon.quantum_state
        time = 0
        random_num = random.random_sample()

        if quantum_state.state == [complex(1), complex(0)]:  # Early
            if random_num <= 0.5:
                time = 0
            else:
                time = self.path_difference
        if quantum_state.state == [complex(0), complex(1)]:  # Late
            if random_num <= 0.5:
                time = self.path_difference
            else:
                time = 2 * self.path_difference

        if random.random_sample() < self.phase_error:
            quantum_state.state = list(multiply([1, -1], quantum_state))

        if quantum_state.state == [complex(sqrt(1/2)), complex(sqrt(1/2))]:  # Early + Late
            if random_num <= 0.25:
                time = 0
            elif random_num <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 0:
                time = self.path_difference
            else:
                return
        if quantum_state.state == [complex(sqrt(1/2)), complex(-sqrt(1/2))]:  # Early - Late
            if random_num <= 0.25:
                time = 0
            elif random_num <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 1:
                time = self.path_difference
            else:
                return

        process = Process(self.receivers[detector_num], "get", [])
        event = Event(self.timeline.now() + time, process)
        self.timeline.schedule(event)