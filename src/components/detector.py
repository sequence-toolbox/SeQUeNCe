"""Models for photon detection devices.

This module models a single photon detector (SPD) for measurement of individual photons.
It also defines a QSDetector class, which combines models of different hardware devices to measure photon states in different bases.
QSDetector is defined as an abstract template and as implementaions for polarization and time bin qubits.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

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
    """Single photon detector device.

    This class models a single photon detector, for detecting photons.
    Can be attached to many different devices to enable different measurement options.

    Attributes:
        name (str): label for detector instance.
        timeline (Timeline): timeline for simulation.
        efficiency (float): probability to successfully measure an incoming photon.
        dark_count (float): average number of false positive detections per second.
        count_rate (float): maximum detection rate; defines detector cooldown time.
        time_resolution (int): minimum resolving power of photon arrival time (in ps).
        photon_counter (int): counts number of detection events.
    """

    def __init__(self, name: str, timeline: "Timeline", efficiency=0.9, dark_count=0, count_rate=int(25e6),
                 time_resolution=150):
        Entity.__init__(self, name, timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = efficiency
        self.dark_count = dark_count  # measured in 1/s
        self.count_rate = count_rate  # measured in Hz
        self.time_resolution = time_resolution  # measured in ps
        self.next_detection_time = -1
        self.photon_counter = 0

    def init(self):
        """Implementation of Entity interface (see base class)."""
        self.add_dark_count()

    def get(self, dark_get=False) -> None:
        """Method to receive a photon for measurement.

        Args:
            dark_get (bool): Signifies if the call is the result of a false positive dark count event.
                If true, will ignore probability calculations (default false).

        Side Effects:
            May notify upper entities of a detection event.
        """

        self.photon_counter += 1
        now = self.timeline.now()
        time = round(now / self.time_resolution) * self.time_resolution

        if (self.get_generator().random() < self.efficiency or dark_get) and now > self.next_detection_time:
            self.notify({'time': time})
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def add_dark_count(self) -> None:
        """Method to schedule false positive detection events.

        Events are scheduled as a Poisson process.

        Side Effects:
            May schedule future `get` method calls.
            May schedule future calls to self.
        """

        if self.dark_count > 0:
            time_to_next = int(self.get_generator().exponential(1 / self.dark_count) * 1e12)  # time to next dark count
            time = time_to_next + self.timeline.now()  # time of next dark count

            process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
            process2 = Process(self, "get", [True])
            event1 = Event(time, process1)
            event2 = Event(time, process2)
            self.timeline.schedule(event1)
            self.timeline.schedule(event2)

    def notify(self, info: Dict[str, Any]):
        """Custom notify function (calls `trigger` method)."""
        for observer in self._observers:
            observer.trigger(self, info)


class QSDetector(Entity, ABC):
    """Abstract QSDetector parent class.

    Provides a template for objects measuring qubits in different encoding schemes.

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        detectors (List[Detector]): list of attached detectors.
        trigger_times (List[List[int]]): tracks simulation time of detection events for each detector.
    """

    def __init__(self, name: str, timeline: "Timeline"):
        Entity.__init__(self, name, timeline)
        self.detectors = []
        self.trigger_times = []

    def update_detector_params(self, detector_id: int, arg_name: str, value: Any) -> None:
        self.detectors[detector_id].__setattr__(arg_name, value)

    @abstractmethod
    def get(self, photon: "Photon") -> None:
        """Abstract method for receiving photons for measurement."""

        pass

    def trigger(self, detector: Detector, info: Dict[str, Any]) -> None:
        detector_index = self.detectors.index(detector)
        self.trigger_times[detector_index].append(info['time'])

    def get_photon_times(self):
        return self.trigger_times

    @abstractmethod
    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        pass


class QSDetectorPolarization(QSDetector):
    """QSDetector to measure polarization encoded qubits.

    There are two detectors.
    Detectors[0] and detectors[1] are directly connected to the beamsplitter.

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        detectors (List[Detector]): list of attached detectors (length 2).
        trigger_times (List[List[int]]): tracks simulation time of detection events for each detector.
        splitter (BeamSplitter): internal beamsplitter object.
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
        """Implementation of Entity interface (see base class)."""

        assert len(self.detectors) == 2
        for d in self.detectors:
            d.owner = self.owner
        self.splitter.owner = self.owner

    def get(self, photon: "Photon") -> None:
        """Method to receive a photon for measurement.

        Forwards the photon to the internal polariaztion beamsplitter.

        Arguments:
            photon (Photon): photon to measure.

        Side Effects:
            Will call `get` method of attached beamsplitter.
        """

        self.splitter.get(photon)

    def get_photon_times(self):
        times, self.trigger_times = self.trigger_times, [[], []]
        return times

    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        self.splitter.set_basis_list(basis_list, start_time, frequency)

    def update_splitter_params(self, arg_name: str, value: Any) -> None:
        self.splitter.__setattr__(arg_name, value)


class QSDetectorTimeBin(QSDetector):
    """QSDetector to measure time bin encoded qubits.

    There are three detectors.
    The switch is connected to detectors[0] and the interferometer.
    The interferometer is connected to detectors[1] and detectors[2].

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        detectors (List[Detector]): list of attached detectors (length 3).
        trigger_times (List[List[int]]): tracks simulation time of detection events for each detector.
        switch (Switch): internal optical switch component.
        interferometer (Interferometer): internal interferometer component.
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
        """Implementation of Entity interface (see base class)."""

        self.interferometer.owner = self.owner
        for d in self.detectors:
            d.owner = self.owner

    def get(self, photon):
        """Method to receive a photon for measurement.

        Forwards the photon to the internal fiber switch.

        Args:
            photon (Photon): photon to measure.

        Side Effects:
            Will call `get` method of attached switch.
        """

        self.switch.get(photon)

    def get_photon_times(self):
        times, self.trigger_times = self.trigger_times, [[], [], []]
        return times

    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        self.switch.set_basis_list(basis_list, start_time, frequency)

    def update_interferometer_params(self, arg_name: str, value: Any) -> None:
        self.interferometer.__setattr__(arg_name, value)

