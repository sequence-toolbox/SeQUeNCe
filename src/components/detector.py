from typing import TYPE_CHECKING, Any

import numpy

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..components.photon import Photon
    from typing import List

from ..components.beam_splitter import BeamSplitter
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process


class Detector(Entity):
    def __init__(self, name: str, timeline: "Timeline", **kwargs):
        Entity.__init__(self, name, timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = kwargs.get("efficiency", 0.9)
        self.dark_count = kwargs.get("dark_count", 0)  # measured in Hz
        self.count_rate = kwargs.get("count_rate", int(25e6))  # measured in Hz
        self.time_resolution = kwargs.get("time_resolution", 150)  # measured in ps
        self.next_detection_time = -1
        self.photon_counter = 0

    def init(self):
        self.add_dark_count()

    def get(self, dark_get=False) -> None:
        self.photon_counter += 1
        now = self.timeline.now()
        time = int(round(now / self.time_resolution) * self.time_resolution)

        if (numpy.random.random_sample() < self.efficiency or dark_get) and now > self.next_detection_time:
            self._pop(detector=self, time=time)
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def add_dark_count(self) -> None:
        if self.dark_count > 0:
            time_to_next = int(numpy.random.exponential(1 / self.dark_count) * 1e12)  # time to next dark count
            time = time_to_next + self.timeline.now()  # time of next dark count

            process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
            process2 = Process(self, "get", [True])
            event1 = Event(time, process1)
            event2 = Event(time, process2)
            self.timeline.schedule(event1)
            self.timeline.schedule(event2)


class QSDetectorPolarization(Entity):
    def __init__(self, name: str, timeline: "Timeline"):
        Entity.__init__(self, name, timeline)
        self.protocols = []
        self.splitter = BeamSplitter(name + ".splitter", timeline)
        self.detectors = [Detector(name + ".detector" + str(i), timeline) for i in range(2)]
        self.splitter.set_receiver(0, self.detectors[0])
        self.splitter.set_receiver(1, self.detectors[1])
        self.children += [self.splitter, self.detectors[0], self.detectors[1]]
        [component.parents.append(self) for component in self.children]
        self.trigger_times = [[], []]

    def init(self) -> None:
        assert len(self.detectors) == 2

    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        self.splitter.set_basis_list(basis_list, start_time, frequency)

    def update_splitter_params(self, arg_name: str, value: Any) -> None:
        self.splitter.__setattr__(arg_name, value)

    def update_detector_params(self, detector_id: int, arg_name: str, value: Any) -> None:
        self.splitter.receivers[detector_id].__setattr__(arg_name, value)

    def get(self, photon: "Photon") -> None:
        self.splitter.get(photon)

    def pop(self, detector: "Detector", time: int) -> None:
        detector_index = self.detectors.index(detector)
        self.trigger_times[detector_index].append(time)

    def get_photon_times(self):
        return self.trigger_times

#
# class QSDetectorTimeBin(Entity):
#     def __init__(self, name, timeline, **kwargs):
#         Entity.__init__(self, name, timeline)
#
#         detectors = kwargs.get("detectors", [])
#         if (self.encoding_type["name"] == "time_bin" and len(detectors) != 3):
#             raise Exception("invalid number of detectors specified")
#         self.detectors = []
#         for d in detectors:
#             if d is not None:
#                 detector = Detector("", timeline, **d)
#             else:
#                 detector = None
#             self.detectors.append(detector)
#
#         # protocol unique initialization
#
#         if self.encoding_type["name"] == "time_bin":
#             from sequence.components.switch import Switch
#             # set up switch and interferometer
#             interferometer = kwargs.get("interferometer")
#             self.interferometer = Interferometer(timeline, **interferometer)
#             self.interferometer.detectors = self.detectors[1:]
#             switch = kwargs.get("switch")
#             self.switch = Switch(timeline, **switch)
#             self.switch.receivers = [self.detectors[0], self.interferometer]
#
#     def init(self):
#         pass
#
#     def get(self, photon):
#         self.switch.get(photon)
#
#     def get_photon_times(self):
#         times = []
#         for d in self.detectors:
#             if d is not None:
#                 times.append(d.photon_times)
#             else:
#                 times.append([])
#         return times
