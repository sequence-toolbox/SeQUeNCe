"""Models for photon detection devices.

This module models a single photon detector (SPD) for measurement of individual photons.
It also defines a QSDetector class, which combines models of different hardware devices to measure photon states in different bases.
QSDetector is defined as an abstract template and as implementaions for polarization and time bin qubits.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

from numpy import random

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..components.photon import Photon
    from typing import List

from ..components.beam_splitter import BeamSplitter
from ..components.switch import Switch
from ..components.interferometer import Interferometer
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process
from ..utils.encoding import time_bin


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
        time = round(now / self.time_resolution) * self.time_resolution

        if (random.random_sample() < self.efficiency or dark_get) and now > self.next_detection_time:
            self.notify({'time': time})
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def add_dark_count(self) -> None:
        if self.dark_count > 0:
            time_to_next = int(random.exponential(1 / self.dark_count) * 1e12)  # time to next dark count
            time = time_to_next + self.timeline.now()  # time of next dark count

            process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
            process2 = Process(self, "get", [True])
            event1 = Event(time, process1)
            event2 = Event(time, process2)
            self.timeline.schedule(event1)
            self.timeline.schedule(event2)

    def notify(self, msg: Dict[str, Any]):
        for observer in self._observers:
            observer.trigger(self, msg)


class QSDetector(Entity, ABC):
    def __init__(self, name: str, timeline: "Timeline"):
        Entity.__init__(self, name, timeline)
        self.protocols = []
        self.detectors = []
        self.trigger_times = []

    def update_detector_params(self, detector_id: int, arg_name: str, value: Any) -> None:
        self.detectors[detector_id].__setattr__(arg_name, value)

    @abstractmethod
    def get(self, photon: "Photon") -> None:
        pass

    def trigger(self, detector: Detector, msg: Dict[str, Any]) -> None:
        detector_index = self.detectors.index(detector)
        self.trigger_times[detector_index].append(msg['time'])

    def get_photon_times(self):
        return self.trigger_times

    @abstractmethod
    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        pass


class QSDetectorPolarization(QSDetector):
    """There are two detectors. Their connections are shown below.

    polarization splitter ---- detectors[0]
                      |------- detectors[1]
    """

    def __init__(self, name: str, timeline: "Timeline"):
        QSDetector.__init__(self, name, timeline)
        self.detectors = [Detector(name + ".detector" + str(i), timeline) for i in range(2)]
        self.splitter = BeamSplitter(name + ".splitter", timeline)
        self.splitter.set_receiver(0, self.detectors[0])
        self.splitter.set_receiver(1, self.detectors[1])
        self.components = [self.splitter, self.detectors[0], self.detectors[1]]
        [component.attach(self) for component in self.components]
        self.trigger_times = [[], []]

    def init(self) -> None:
        assert len(self.detectors) == 2

    def get(self, photon: "Photon") -> None:
        self.splitter.get(photon)

    def get_photon_times(self):
        times, self.trigger_times = self.trigger_times, [[], []]
        return times

    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        self.splitter.set_basis_list(basis_list, start_time, frequency)

    def update_splitter_params(self, arg_name: str, value: Any) -> None:
        self.splitter.__setattr__(arg_name, value)


class QSDetectorTimeBin(QSDetector):
    """There are three detectors. Their connections are shown below.

    switch ---- detectors[0]
        |------ interferometer ---- detectors[1]
                            |------ detectors[2]
    """

    def __init__(self, name: str, timeline: "Timeline"):
        QSDetector.__init__(self, name, timeline)
        self.switch = Switch(name + ".switch", timeline)
        self.detectors = [Detector(name + ".detector" + str(i), timeline) for i in range(3)]
        self.switch.set_detector(self.detectors[0])
        self.interferometer = Interferometer(name + ".interferometer", timeline, time_bin["bin_separation"])
        self.interferometer.set_receiver(0, self.detectors[1])
        self.interferometer.set_receiver(1, self.detectors[2])
        self.switch.set_interferometer(self.interferometer)

        self.components = [self.switch, self.interferometer] + self.detectors
        [component.attach(self) for component in self.components]
        self.trigger_times = [[], [], []]

    def init(self):
        pass

    def get(self, photon):
        self.switch.get(photon)

    def get_photon_times(self):
        times, self.trigger_times = self.trigger_times, [[], [], []]
        return times

    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        self.switch.set_basis_list(basis_list, start_time, frequency)

    def update_interferometer_params(self, arg_name: str, value: Any) -> None:
        self.interferometer.__setattr__(arg_name, value)
